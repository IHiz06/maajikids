"""
MaajiKids — Servicio de IA (google-genai 1.x / Gemini 2.5 Flash)
Dos módulos: generador de recomendaciones y asistente conversacional Maaji.
"""
import logging
import google.genai as genai
from flask import current_app

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"

# ── System prompts ─────────────────────────────────────────────────────────────
RECOMMENDATIONS_SYSTEM_PROMPT = """Eres un especialista en estimulación temprana y desarrollo infantil.
Analiza la siguiente evaluación de desarrollo de un niño/a e identifica las áreas de menor puntaje.
Genera recomendaciones prácticas y actividades personalizadas para padres de familia.
Estructura tu respuesta con: RESUMEN DEL DESARROLLO, ÁREAS DE FORTALEZA, ÁREAS A ESTIMULAR y ACTIVIDADES RECOMENDADAS.
Usa lenguaje claro, empático y sin tecnicismos. Responde siempre en español.
NO incluyas datos sensibles médicos ni información de contacto."""

MAAJI_SYSTEM_PROMPT = """Eres 'Maaji', el asistente virtual del Centro MaajiKids.
Eres amable, empático y especializado en desarrollo infantil temprano.
Tu único propósito es:
• Informar sobre el centro MaajiKids, sus talleres y servicios.
• Orientar sobre los beneficios de la estimulación temprana para niños de 0 a 6 años.
• Ayudar a padres a conocer el proceso de inscripción.
• Recomendar el registro si el usuario desea inscribir a su hijo.
RESTRICCIÓN ESTRICTA: Si el usuario hace preguntas no relacionadas con MaajiKids, desarrollo infantil o inscripción, responde:
"Soy Maaji, el asistente del Centro MaajiKids. Solo puedo ayudarte con información sobre nuestros talleres y el desarrollo infantil. ¿En qué puedo orientarte?"
La edad máxima para inscribir niños en MaajiKids es 6 años.
Responde siempre en español, de forma clara y sin tecnicismos.
NO tienes acceso a notas, evaluaciones, datos médicos, pagos ni información privada."""


def _get_client() -> genai.Client:
    api_key = current_app.config.get("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)


def generate_recommendations(
    child_name: str,
    age_months: int,
    score_cognitive: float,
    score_motor: float,
    score_language: float,
    score_social: float,
    observations: str | None = None,
    workshop_title: str = "",
) -> str | None:
    """
    Genera recomendaciones personalizadas de desarrollo infantil.
    Retorna el texto generado o None si falla.
    """
    try:
        client = _get_client()

        prompt = f"""
{RECOMMENDATIONS_SYSTEM_PROMPT}

DATOS DE LA EVALUACIÓN:
- Niño/a: {child_name}
- Edad: {age_months} meses ({round(age_months/12, 1)} años)
- Taller: {workshop_title}
- Puntajes (escala 0-10):
  • Cognitivo: {score_cognitive}
  • Motor: {score_motor}
  • Lenguaje: {score_language}
  • Socioemocional: {score_social}
  • Promedio: {round((score_cognitive + score_motor + score_language + score_social) / 4, 2)}
"""
        if observations:
            prompt += f"\nObservaciones del profesor:\n{observations}"

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
        return response.text

    except Exception as e:
        logger.error(f"[AI] Error generando recomendaciones: {e}")
        return None


def chat_with_maaji(
    messages: list[dict],
    active_workshops: list[dict] | None = None,
    parent_children: list[dict] | None = None,
) -> str | None:
    """
    Responde al usuario en el chat conversacional de Maaji.

    Args:
        messages: Lista de dicts [{"role": "user"|"model", "parts": [{"text": "..."}]}]
        active_workshops: Lista de talleres activos para contexto
        parent_children: Hijos del parent autenticado (si aplica)

    Retorna el texto de respuesta o None si falla.
    """
    try:
        client = _get_client()

        # Construye contexto del sistema
        system_parts = MAAJI_SYSTEM_PROMPT

        if active_workshops:
            ws_list = "\n".join([
                f"  • {w['title']} — Edad: {w['age_min']}-{w['age_max']} meses "
                f"— Precio: S/ {w['price']} — Cupos: {w['available_spots']}"
                for w in active_workshops[:10]  # Máx. 10 talleres en contexto
            ])
            system_parts += f"\n\nTALLERES ACTIVOS DISPONIBLES:\n{ws_list}"

        if parent_children:
            ch_list = "\n".join([
                f"  • {c['full_name']} ({c['age_months']} meses)"
                for c in parent_children
            ])
            system_parts += f"\n\nHIJOS DEL PADRE/MADRE REGISTRADOS:\n{ch_list}"

        # Usa generate_content con historial completo
        response = client.models.generate_content(
            model=MODEL,
            contents=messages,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_parts,
            ),
        )
        return response.text

    except Exception as e:
        logger.error(f"[AI] Error en chat Maaji: {e}")
        return None
