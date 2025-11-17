import json
from pathlib import Path
from typing import Dict, List

import httpx

from utils.helpers import setup_logger, parse_timestamp, format_timestamp


class ClipSelector:
    """Uses an LLM to select viral-worthy clips from a transcript."""

    def __init__(
        self,
        api_key: str,
        model: str,
        job_folder: Path,
        min_duration: int = 15,
        max_duration: int = 60,
        target_clips: int = 5,
    ):
        self.api_key = api_key
        self.model = model
        self.job_folder = job_folder
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.target_clips = target_clips
        self.logger = setup_logger("ClipSelector", job_folder / "processing.log")

    async def select_clips(self, transcript: Dict) -> List[Dict]:
        """
        Analyze transcript and select viral-worthy clips.

        Returns:
            List of clip suggestions with timestamps and reasons.
        """
        self.logger.info("Analyzing transcript for viral clips")

        base_prompt = self._build_viral_prompt(transcript)
        prompt = base_prompt

        best_clips: List[Dict] = []
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            self.logger.info(
                f"LLM selection attempt {attempt}/{max_attempts} "
                f"(target {self.target_clips} clips)"
            )

            try:
                raw_clips = await self._call_llm(prompt)
            except Exception as e:
                self.logger.error(f"Attempt {attempt} failed: {e}")
                raw_clips = []

            clips = self._dedupe_and_limit_clips(raw_clips)

            self.logger.info(
                f"Attempt {attempt}: {len(clips)} valid, non-overlapping clips"
            )

            if len(clips) > len(best_clips):
                best_clips = clips

            if len(best_clips) >= self.target_clips:
                break

            # Build feedback prompt for next attempt
            prompt = (
                base_prompt
                + f"""

PREVIOUS ATTEMPT FEEDBACK:
- You only returned {len(clips)} valid, non-overlapping clips.
- You MUST now return at least {self.target_clips} non-overlapping clips.
- If necessary, choose slightly less perfect but still engaging segments
  to reach {self.target_clips} clips.
- All clips must still be between {self.min_duration} and {self.max_duration}
  seconds and respect the JSON format exactly.
"""
            )

        # Save clip suggestions for inspection
        suggestions_path = self.job_folder / "clip_suggestions.json"
        with open(suggestions_path, "w", encoding="utf-8") as f:
            json.dump(best_clips, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Selected {len(best_clips)} clips")
        return best_clips

    def _build_viral_prompt(self, transcript: Dict) -> str:
        """
        Build LLM prompt based on viral short-form criteria.
        """
        transcript_text = self._format_transcript(transcript)

        prompt = f"""Analyze the following Hindi video transcript and identify {self.target_clips} viral-worthy clips for Instagram Reels and YouTube Shorts.

The clips must:
- Be between {self.min_duration} and {self.max_duration} seconds long
- Have a strong hook in the first 3 seconds
- Contain a complete, self-contained narrative
- Include an emotional or insight-driven payoff

TRANSCRIPT:
{transcript_text}
"""
        return prompt

    def _format_transcript(self, transcript: Dict) -> str:
        """Format transcript segments with timestamps for LLM analysis."""
        segments = transcript.get("segments", [])

        formatted = []
        for seg in segments:
            start = self._format_time(seg["start"])
            end = self._format_time(seg["end"])
            text = seg["text"].strip()
            formatted.append(f"[{start} - {end}] {text}")

        return "\n".join(formatted)

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _get_system_message(self) -> str:
        """
        Load the system prompt for clip selection from an external template.

        This keeps the long instructions out of the code and makes it easier
        to iterate on the messaging without touching Python logic.
        """
        base_dir = Path(__file__).resolve().parent.parent
        template_path = base_dir / "prompts" / "clip_selector_system.txt"

        try:
            template = template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            # Fallback: minimal inline system message if template is missing
            self.logger.warning(
                "System prompt template not found; using minimal inline message."
            )
            template = (
                "You are an expert at selecting viral short-form clips. "
                f"Always return JSON with clips between {self.min_duration} and "
                f"{self.max_duration} seconds."
            )

        return template.format(min_d=self.min_duration, max_d=self.max_duration)

    async def _call_llm(self, prompt: str) -> List[Dict]:
        """Call OpenRouter API with viral clip selection prompt."""
        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Automated Shorts Generator",
        }

        system_message = self._get_system_message()

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            # More deterministic behavior so constraints are followed
            "temperature": 0.25,
            "top_p": 0.8,
            "max_tokens": 20000,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()

                result = response.json()

                self.logger.info(
                    f"OpenRouter response keys: {list(result.keys())}"
                )
                self.logger.info(
                    f"Full response: {json.dumps(result, indent=2)[:1000]}"
                )

                message = result["choices"][0]["message"]
                content = message.get("content") or ""
                reasoning = message.get("reasoning") or ""

                self.logger.info(
                    f"LLM content length: {len(content) if content else 0}"
                )
                self.logger.info(
                    f"LLM content preview: {content[:500] if content else 'EMPTY'}"
                )
                if reasoning:
                    self.logger.info(
                        f"LLM reasoning length: {len(reasoning)}"
                    )
                    self.logger.info(
                        f"LLM reasoning preview: {reasoning[:500]}"
                    )

                raw_text = content if content.strip() else reasoning

                # Strip possible markdown fences
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0]
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0]

                clips_data = json.loads(raw_text.strip())
                raw_clips = clips_data.get("clips", [])

                self.logger.info(f"LLM suggested {len(raw_clips)} clips")

                return raw_clips

            except httpx.HTTPError as e:
                self.logger.error(f"HTTP error calling LLM: {e}")
                if getattr(e, "response", None) is not None:
                    self.logger.error(
                        f"Response status: {e.response.status_code}"
                    )
                    self.logger.error(f"Response body: {e.response.text}")
                raise Exception(f"LLM API call failed: {e}")
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {e}")
                self.logger.error(f"Raw response: {raw_text}")
                raise Exception(f"LLM returned invalid JSON: {e}")
            except Exception as e:
                self.logger.error(f"Error calling LLM: {e}")
                raise

    def _normalize_and_validate_clips(self, clips: List[Dict]) -> List[Dict]:
        """
        Ensure all clips respect duration bounds and have consistent timestamps.

        - Recomputes duration_seconds from end_time - start_time
        - Keeps only clips within [min_duration, max_duration]
        - Drops clips that are structurally invalid (missing times, negative ranges)
        """
        normalized: List[Dict] = []
        dropped: List[Dict] = []

        for clip in clips:
            start_str = clip.get("start_time")
            end_str = clip.get("end_time")

            if not start_str or not end_str:
                dropped.append(
                    {"clip": clip, "reason": "Missing start_time or end_time"}
                )
                continue

            try:
                start_s = parse_timestamp(start_str)
                end_s = parse_timestamp(end_str)
            except Exception as e:
                dropped.append({"clip": clip, "reason": f"Invalid timestamps: {e}"})
                continue

            duration = max(0.0, end_s - start_s)
            if duration <= 0:
                dropped.append({"clip": clip, "reason": "Non-positive duration"})
                continue

            if duration > self.max_duration or duration < self.min_duration:
                dropped.append(
                    {
                        "clip": clip,
                        "reason": (
                            f"Duration {duration:.1f}s outside "
                            f"[{self.min_duration},{self.max_duration}]"
                        ),
                    }
                )
                continue

            clip["start_time"] = format_timestamp(start_s)
            clip["end_time"] = format_timestamp(end_s)
            clip["duration_seconds"] = int(round(duration))

            normalized.append(clip)

        if dropped:
            self.logger.info(
                f"Duration normalization: {len(normalized)} kept, "
                f"{len(dropped)} dropped"
            )

        return normalized

    def _dedupe_and_limit_clips(self, clips: List[Dict]) -> List[Dict]:
        """
        Remove structurally invalid / out-of-range clips, de-duplicate
        overlapping segments, and cap the result at target_clips.
        """
        normalized = self._normalize_and_validate_clips(clips)

        if not normalized:
            return []

        # Sort by start time
        def start_time_s(c: Dict) -> float:
            return parse_timestamp(c["start_time"])

        normalized.sort(key=start_time_s)

        # Keep non-overlapping clips (allowing up to 1s overlap buffer)
        non_overlapping: List[Dict] = []
        last_end: float = -1.0
        overlap_buffer = 1.0

        for clip in normalized:
            s = parse_timestamp(clip["start_time"])
            e = parse_timestamp(clip["end_time"])

            if last_end < 0 or s >= last_end - overlap_buffer:
                non_overlapping.append(clip)
                last_end = e
            else:
                self.logger.info(
                    "Dropping overlapping clip "
                    f"{clip.get('title', '(untitled)')} "
                    f"[{clip['start_time']} - {clip['end_time']}]"
                )

        if not non_overlapping:
            return []

        # Sort by virality_score (highest first) and cap at target_clips
        def score(c: Dict) -> float:
            try:
                return float(c.get("virality_score", 0) or 0)
            except Exception:
                return 0.0

        non_overlapping.sort(key=score, reverse=True)

        if len(non_overlapping) > self.target_clips:
            non_overlapping = non_overlapping[: self.target_clips]

        return non_overlapping
