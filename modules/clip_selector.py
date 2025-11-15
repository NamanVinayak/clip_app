import httpx
import json
from pathlib import Path
from typing import Dict, List
from utils.helpers import setup_logger


class ClipSelector:
    """Uses LLM to select viral-worthy clips from transcript"""

    def __init__(
        self,
        api_key: str,
        model: str,
        job_folder: Path,
        min_duration: int = 15,
        max_duration: int = 60,
        target_clips: int = 5
    ):
        self.api_key = api_key
        self.model = model
        self.job_folder = job_folder
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.target_clips = target_clips
        self.logger = setup_logger(
            "ClipSelector",
            job_folder / "processing.log"
        )

    async def select_clips(self, transcript: Dict) -> List[Dict]:
        """
        Analyze transcript and select viral-worthy clips

        Returns:
            List of clip suggestions with timestamps and reasons
        """
        self.logger.info("Analyzing transcript for viral clips")

        # Build prompt based on OpusClip methodology
        prompt = self._build_viral_prompt(transcript)

        # Call LLM via OpenRouter
        clips = await self._call_llm(prompt)

        # Save clip suggestions
        suggestions_path = self.job_folder / "clip_suggestions.json"
        with open(suggestions_path, 'w', encoding='utf-8') as f:
            json.dump(clips, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Selected {len(clips)} clips")
        return clips

    def _build_viral_prompt(self, transcript: Dict) -> str:
        """
        Build LLM prompt based on OpusClip viral criteria

        Focus on:
        - Strong hooks (first 3 seconds)
        - Complete thoughts (15-60 seconds)
        - Emotional peaks
        - Platform-specific optimization
        """
        # Format transcript segments for LLM
        transcript_text = self._format_transcript(transcript)

        prompt = f"""You are an expert at identifying viral-worthy clips for Instagram Reels and YouTube Shorts.

Analyze this Hindi video transcript and identify {self.target_clips} viral-worthy clips.

TRANSCRIPT:
{transcript_text}

SELECTION CRITERIA:

1. STRONG HOOK (First 3 seconds)
   - Emotional/dramatic opening statement
   - Intriguing question or controversial claim
   - Stunning visual moment or problem statement
   - Must capture attention immediately

2. HOOK TYPES TO LOOK FOR:
   - Curiosity Hook: Creates intrigue without revealing the complete story
   - Controversy Hook: Polarizing statement that generates immediate engagement
   - Problem-Solution Hook: Addresses specific pain point (leverages loss aversion)
   - Emotional Hook: Strong emotional reaction in opening

3. COMPLETE THOUGHT (Self-contained narrative)
   - Duration: {self.min_duration}-45 seconds MAXIMUM (Instagram/YouTube Shorts optimal length)
   - CRITICAL: Clips MUST be 45 seconds or less - this is NON-NEGOTIABLE
   - Prefer 20-35 second clips for maximum engagement
   - Has clear beginning, middle, and end
   - No mid-sentence cuts
   - Delivers complete value/insight in shortest possible time
   - Satisfying conclusion or clear call to action

4. EMOTIONAL PEAKS
   - Moments of high energy or emotion
   - Valuable insights or "aha" moments
   - Controversial or thought-provoking statements
   - Relatable experiences

5. PLATFORM OPTIMIZATION
   - High information density (value per second)
   - Fast-paced with no dead air
   - Suitable for short-form consumption
   - Re-watchable content

IMPORTANT:
- Prefer clips with modest, authentic claims over exaggerated promises
- Look for transitional hooks that build curiosity throughout
- Ensure each clip can stand alone without context
- Prioritize complete thoughts over viral moments alone

OUTPUT FORMAT (JSON only, no explanation):
{{
  "clips": [
    {{
      "start_time": "HH:MM:SS",
      "end_time": "HH:MM:SS",
      "duration_seconds": 30,
      "virality_score": 8.5,
      "hook_type": "problem-solution",
      "title": "Brief attention-grabbing title",
      "reason": "Why this clip is viral-worthy (mention hook quality, emotional arc, and completion)",
      "first_3_seconds": "What happens in the critical opening"
    }}
  ]
}}

Return ONLY valid JSON, no markdown formatting or explanation."""

        return prompt

    def _format_transcript(self, transcript: Dict) -> str:
        """Format transcript segments with timestamps for LLM analysis"""
        segments = transcript.get('segments', [])

        formatted = []
        for seg in segments:
            start = self._format_time(seg['start'])
            end = self._format_time(seg['end'])
            text = seg['text'].strip()
            formatted.append(f"[{start} - {end}] {text}")

        return '\n'.join(formatted)

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    async def _call_llm(self, prompt: str) -> List[Dict]:
        """Call OpenRouter API with viral clip selection prompt"""
        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",  # Your app URL
            "X-Title": "Automated Shorts Generator"
        }

        system_message = """You are a viral short-form content expert who has analyzed thousands of successful Instagram Reels and YouTube Shorts.

PLATFORM KNOWLEDGE:
- Instagram Reels & YouTube Shorts are 15-60 second vertical videos (9:16 aspect ratio)
- Average watch time: 8-12 seconds (most viewers scroll within 10 seconds)
- The FIRST 3 SECONDS determine if someone keeps watching or scrolls
- Optimal clip length: 20-35 seconds (engagement drops after 45 seconds)
- Shorts algorithm prioritizes: watch time %, replays, and completion rate

WHAT MAKES SHORTS GO VIRAL:
1. INSTANT HOOK (0-3 sec): Pattern interrupts that stop the scroll
   - Controversial statements: "I'm blocking my entire family"
   - Bold claims: "This changed everything for me"
   - Curiosity gaps: "Nobody talks about this..."
   - Emotional openness: "I need to be honest about..."

2. RETENTION TACTICS (3-30 sec):
   - Fast pacing (no pauses longer than 2 seconds)
   - Building tension or curiosity
   - Relatable pain points or experiences
   - Visual variety (movement, gestures, changing scenes)

3. SATISFYING PAYOFF (final 5-10 sec):
   - Clear conclusion or revelation
   - Emotional resolution
   - Actionable insight
   - Cliffhanger that prompts replay

CLIP SELECTION RULES:
✅ DO SELECT:
- Clips with strong emotional moments (vulnerability, anger, joy)
- Self-contained stories that need no context
- Controversial or polarizing opinions
- Relatable struggles or "me too" moments
- Clips that answer: "Why should I keep watching?"

❌ DO NOT SELECT:
- Long explanations or backstories
- Mid-conversation clips that need context
- Clips with weak or slow openings
- Content that takes >10 seconds to get interesting
- Generic advice without personal stakes

RESPONSE FORMAT:
Always return ONLY valid JSON. No markdown, no explanation, just:
{"clips": [{"start_time": "HH:MM:SS", "end_time": "HH:MM:SS", ...}]}"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()

                result = response.json()

                # Log the full response for debugging
                self.logger.info(f"OpenRouter response keys: {list(result.keys())}")
                self.logger.info(f"Full response: {json.dumps(result, indent=2)[:1000]}")

                content = result['choices'][0]['message']['content']

                self.logger.info(f"LLM content length: {len(content) if content else 0}")
                self.logger.info(f"LLM content preview: {content[:500] if content else 'EMPTY'}")

                # Parse JSON response
                # Remove markdown code blocks if present
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]

                clips_data = json.loads(content.strip())
                clips = clips_data.get('clips', [])

                self.logger.info(f"LLM suggested {len(clips)} clips")

                # STRICT VALIDATION: Enforce max duration limit
                validated_clips = []
                rejected_clips = []

                for clip in clips:
                    duration = clip.get('duration_seconds', 0)

                    # Enforce HARD maximum of 45 seconds (config max_duration)
                    if duration > self.max_duration:
                        rejected_clips.append({
                            'clip': clip,
                            'reason': f"Duration {duration}s exceeds maximum {self.max_duration}s"
                        })
                        self.logger.warning(f"Rejected clip '{clip.get('title', 'Untitled')}': "
                                          f"Duration {duration}s > {self.max_duration}s max")
                    elif duration < self.min_duration:
                        rejected_clips.append({
                            'clip': clip,
                            'reason': f"Duration {duration}s below minimum {self.min_duration}s"
                        })
                        self.logger.warning(f"Rejected clip '{clip.get('title', 'Untitled')}': "
                                          f"Duration {duration}s < {self.min_duration}s min")
                    else:
                        validated_clips.append(clip)

                if rejected_clips:
                    self.logger.info(f"Validation: {len(validated_clips)} accepted, {len(rejected_clips)} rejected")

                if not validated_clips:
                    self.logger.error("No clips passed validation! Using original clips anyway.")
                    return clips

                return validated_clips

            except httpx.HTTPError as e:
                self.logger.error(f"HTTP error calling LLM: {e}")
                if hasattr(e, 'response') and e.response:
                    self.logger.error(f"Response status: {e.response.status_code}")
                    self.logger.error(f"Response body: {e.response.text}")
                raise Exception(f"LLM API call failed: {e}")
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {e}")
                self.logger.error(f"Raw response: {content}")
                raise Exception(f"LLM returned invalid JSON: {e}")
            except Exception as e:
                self.logger.error(f"Error calling LLM: {e}")
                raise
