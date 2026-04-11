import json
import time
from pathlib import Path
from typing import Callable


class WhisperRunner:
    """Wrapper síncrono ao redor de `openai-whisper`. Deve ser chamado de um executor."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_name)
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        output_dir: Path,
        progress_cb: Callable[[float, str], None] | None = None,
    ) -> dict:
        import whisper
        from whisper.utils import get_writer

        model = self._load()
        started = time.time()

        result = model.transcribe(
            str(audio_path), language="pt", verbose=False,
        )

        # Emissão de progresso após cada 10% dos segmentos. O whisper não expõe
        # callback nativo — interpolamos pelo end time do último segmento.
        if progress_cb and result.get("segments"):
            total = result["segments"][-1]["end"] or 1.0
            # callback único com 100% (execução síncrona acabou)
            progress_cb(1.0, f"{len(result['segments'])} segmentos em {int(total)}s de audio")

        output_dir.mkdir(parents=True, exist_ok=True)
        writer = get_writer("vtt", str(output_dir))
        writer(result, "transcricao.wav", {
            "max_line_width": None,
            "max_line_count": None,
            "highlight_words": False,
        })

        (output_dir / "reuniao_transcript.txt").write_text(result["text"], encoding="utf-8")

        segs = [
            {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
            for s in result["segments"]
        ]
        (output_dir / "reuniao_segments.json").write_text(
            json.dumps(segs, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        wall_time = int(time.time() - started)
        return {
            "wall_time_s": wall_time,
            "audio_duration_s": int(result["segments"][-1]["end"]) if result["segments"] else 0,
            "text": result["text"],
            "segments": segs,
            "vtt_path": output_dir / "transcricao.vtt",
        }
