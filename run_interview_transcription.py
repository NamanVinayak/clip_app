import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from config import settings
from utils.helpers import setup_logger, create_job_folder
from modules.transcriber import Transcriber
from modules.clip_selector import ClipSelector # To reuse LLM call logic

# --- System Prompts ---

WHISPER_SYSTEM_PROMPT = """This is an audio recording of a sales job interview.
There are two speakers: an interviewer asking questions and a candidate providing answers.
Please transcribe the conversation as accurately as possible.
The output should clearly distinguish between the two speakers.
"""

LLM_FORMATTING_SYSTEM_PROMPT = """You are an expert transcript editor.
You will be given a raw transcript from a job interview with speaker labels (e.g., SPEAKER_00, SPEAKER_01).
Your task is to reformat this transcript into a clean, readable Q&A format.

Follow these rules exactly:
1.  The interviewer's speech should be converted into a concise question prefixed with "Qn)", where 'n' is the question number.
2.  The candidate's speech should be presented as the answer, following the question.
3.  Maintain the candidate's response exactly as it is in the transcript. Do not summarize or change their words.
4.  Each question and its corresponding answer should be separated by a double newline.
5.  Identify the speakers correctly. The interviewer asks short questions, and the candidate gives long, detailed answers.

Example Input:
[00:00:01 - 00:00:03] SPEAKER_00: To start with, can you tell me about yourself?
[00:00:04 - 00:01:05] SPEAKER_01: Yes, no problem at all... (long answer)...

Example Output:
Q1) To start with, can you tell me about yourself?

Yes, no problem at all... (long answer)...
"""

# --- Helper Functions ---

def process_diarized_transcript_for_llm(transcript_data: Dict) -> str:
    """
    Converts the diarized JSON transcript into a single string for the LLM.
    """
    segments = transcript_data.get('segments', [])
    output_lines = []
    for segment in segments:
        speaker = segment.get('speaker', 'UNKNOWN')
        # WhisperX returns floats, round to int for cleaner display
        start_s = int(segment.get('start', 0))
        end_s = int(segment.get('end', 0))
        text = segment.get('text', '').strip()
        
        # Format for LLM input
        line = f"[{start_s:04d}-{end_s:04d}] {speaker}: {text}"
        output_lines.append(line)
        
    return "\n".join(output_lines)

async def call_openrouter_llm(
    prompt_text: str, job_folder: Path, logger: Any
) -> str:
    """
    Calls OpenRouter LLM for formatting.
    Adapts logic from ClipSelector._call_llm.
    """
    logger.info("Sending transcript to OpenRouter for formatting...")

    llm_caller = ClipSelector(
        api_key=settings.openrouter_api_key,
        model=settings.llm_model,
        job_folder=job_folder # Pass job_folder for logging/debugging
    )
    # This is a simplified call without response_format and other clip-specific logic
    # We will directly call the internal _call_llm which is robust
    # The actual implementation of _call_llm expects system/user messages in payload,
    # so we need to construct it similarly.

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {llm_caller.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000", # As used in original clip_selector
        "X-Title": "Automated Shorts Generator", # As used in original clip_selector
    }

    payload = {
        "model": llm_caller.model,
        "messages": [
            {"role": "system", "content": LLM_FORMATTING_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
        # No response_format for plain text output
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            formatted_text = result["choices"][0]["message"]["content"]
            logger.info("Formatted transcript received from OpenRouter.")
            
            # Save for debugging
            llm_output_path = job_folder / "llm_formatted_output.txt"
            with open(llm_output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
            
            return formatted_text.strip()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling OpenRouter: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response body: {e.response.text}")
            raise
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Log the raw response if possible for debugging JSONDecodeError
            if 'result' in locals() and isinstance(result, dict):
                logger.error(f"Raw OpenRouter response: {json.dumps(result, indent=2)}")
            raise
        except Exception as e:
            logger.error(f"Error calling OpenRouter LLM: {e}")
            raise


# --- Main Execution ---

async def main():
    """
    Main function to run the interview transcription and formatting process.
    """
    audio_file = Path("/Users/naman/Downloads/SALES Interview Questions & Answers! (How to PASS a Sales Interview!) - CareerVidz.mp3")
    
    if not audio_file.exists():
        print(f"ERROR: Audio file not found at {audio_file}")
        return

    job_folder = create_job_folder(settings.outputs_dir)
    logger = setup_logger("InterviewProcessor", job_folder / "process.log")

    try:
        # 1. Transcribe with diarization using the modified Transcriber
        transcriber_instance = Transcriber(
            api_key=settings.runpod_api_key,
            endpoint=settings.runpod_endpoint,
            job_folder=job_folder
        )
        diarized_transcript = await transcriber_instance.transcribe(
            audio_path=audio_file,
            initial_prompt=WHISPER_SYSTEM_PROMPT,
            language='en'
        )
        
        # 2. Process raw transcript for LLM input
        raw_text_for_llm = process_diarized_transcript_for_llm(diarized_transcript)
        
        if not raw_text_for_llm:
            logger.error("Transcription resulted in empty text or no segments. Aborting.")
            return
            
        # 3. Format transcript using OpenRouter LLM
        final_formatted_transcript = await call_openrouter_llm(
            raw_text_for_llm, job_folder, logger
        )

        # 4. Save the final formatted transcript
        output_path = job_folder / "formatted_interview_transcript.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_formatted_transcript)
            
        print("\n--- Transcription and Formatting Complete ---")
        print(f"✅ Final formatted transcript saved to: {output_path}")
        print(f"✅ SRT file saved to: {job_folder / 'transcript.srt'}")
        print(f"✅ Raw diarized JSON saved to: {job_folder / 'transcript.json'}") # Note: Renamed from transcript_raw_diarized.json
        print("-------------------------------------------\\n")

    except Exception as e:
        logger.error(f"An error occurred in the main process: {e}", exc_info=True)
        print(f"\n--- An Error Occurred ---")
        print(f"❌ Process failed. See logs for details: {job_folder / 'process.log'}")
        print("---------------------------\\n")


if __name__ == "__main__":
    # Check for API keys
    if not settings.runpod_api_key or not settings.openrouter_api_key:
        print("ERROR: RUNPOD_API_KEY and OPENROUTER_API_KEY must be set in your .env file.")
    else:
        asyncio.run(main())
