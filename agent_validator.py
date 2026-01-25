"""
Agent Validator - Validador de Custom Agents para Copilot SDK

Este módulo permite validar agentes personalizados comparando sus respuestas
con el agente base y verificando que cumplen con las expectativas definidas.

Incluye:
- Comparación histórica entre ejecuciones
- Detección de regresiones
- Tracking de mejoras/empeoramientos por test
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from copilot import CopilotClient


@dataclass
class TestCase:
    """Representa un caso de prueba para el agente."""
    name: str
    prompt: str
    expected_contains: list[str] = field(default_factory=list)
    expected_not_contains: list[str] = field(default_factory=list)
    expected_behavior: str = ""  # Descripción de comportamiento esperado para LLM-as-judge


@dataclass
class AgentDefinition:
    """Definición de un agente desde markdown."""
    name: str
    display_name: str
    description: str
    prompt: str
    tools: list[str]
    test_cases: list[TestCase]


@dataclass
class TestResult:
    """Resultado de una prueba individual."""
    test_name: str
    passed: bool
    response: str
    latency_ms: float
    contains_passed: list[str]
    contains_failed: list[str]
    not_contains_passed: list[str]
    not_contains_failed: list[str]
    error: str | None = None
    # Evaluación LLM-as-judge
    llm_score: float = 0.0  # 0-100 score semántico
    llm_passed: bool = False
    llm_reasoning: str = ""  # Explicación del juicio


@dataclass
class ValidationReport:
    """Reporte completo de validación."""
    agent_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    avg_latency_ms: float
    score: float
    results: list[TestResult]
    created_files: list[str] = field(default_factory=list)
    baseline_comparison: dict[str, Any] | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HistoricalComparison:
    """Comparación con ejecución anterior."""
    previous_score: float
    current_score: float
    score_diff: float
    previous_passed: int
    current_passed: int
    passed_diff: int
    previous_latency: float
    current_latency: float
    latency_diff: float
    regressions: list[str]  # Tests que antes pasaban y ahora fallan
    improvements: list[str]  # Tests que antes fallaban y ahora pasan
    is_regression: bool  # True si el score bajó significativamente


def parse_agent_markdown(file_path: Path) -> AgentDefinition:
    """
    Parsea un archivo markdown con la definición del agente.
    
    Args:
        file_path: Ruta al archivo markdown
        
    Returns:
        AgentDefinition con toda la configuración
    """
    content = file_path.read_text(encoding="utf-8")
    
    # Extraer metadata
    name = _extract_field(content, r"\*\*name\*\*:\s*(\w+)")
    display_name = _extract_field(content, r"\*\*display_name\*\*:\s*(.+)")
    description = _extract_field(content, r"\*\*description\*\*:\s*(.+)")
    
    # Extraer prompt (entre ## Prompt y ## Tools)
    prompt_match = re.search(r"## Prompt\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    prompt = prompt_match.group(1).strip() if prompt_match else ""
    
    # Extraer tools
    tools_match = re.search(r"## Tools\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    tools = []
    if tools_match:
        tools = [line.strip("- ").strip() for line in tools_match.group(1).strip().split("\n") if line.strip().startswith("-")]
    
    # Extraer test cases
    test_cases = _parse_test_cases(content)
    
    return AgentDefinition(
        name=name or "unknown",
        display_name=display_name or name or "Unknown Agent",
        description=description or "",
        prompt=prompt,
        tools=tools,
        test_cases=test_cases
    )


def _extract_field(content: str, pattern: str) -> str | None:
    """Extrae un campo usando regex."""
    match = re.search(pattern, content)
    return match.group(1).strip() if match else None


def _parse_test_cases(content: str) -> list[TestCase]:
    """Parsea los casos de prueba del markdown."""
    test_cases = []
    
    # Buscar sección de Test Cases
    tests_match = re.search(r"## Test Cases\s*\n(.*)", content, re.DOTALL)
    if not tests_match:
        return test_cases
    
    tests_content = tests_match.group(1)
    
    # Buscar cada test case
    test_pattern = r"### (test_\w+)\s*\n\*\*prompt\*\*:\s*(.+?)(?=\n\*\*expected)"
    expected_contains_pattern = r"\*\*expected_contains\*\*:\s*\n((?:- .+\n?)+)"
    expected_not_contains_pattern = r"\*\*expected_not_contains\*\*:\s*\n((?:- .+\n?)+)"
    expected_behavior_pattern = r"\*\*expected_behavior\*\*:\s*(.+?)(?=\n\*\*|\n###|\Z)"
    
    # Dividir por tests
    test_blocks = re.split(r"(?=### test_)", tests_content)
    
    for block in test_blocks:
        if not block.strip() or not block.strip().startswith("### test_"):
            continue
            
        # Nombre del test
        name_match = re.search(r"### (test_\w+)", block)
        if not name_match:
            continue
        name = name_match.group(1)
        
        # Prompt
        prompt_match = re.search(r"\*\*prompt\*\*:\s*(.+?)(?=\n\*\*|$)", block, re.DOTALL)
        prompt = prompt_match.group(1).strip() if prompt_match else ""
        
        # Expected contains
        contains = []
        contains_match = re.search(expected_contains_pattern, block)
        if contains_match:
            contains = [line.strip("- ").strip() for line in contains_match.group(1).strip().split("\n") if line.strip().startswith("-")]
        
        # Expected not contains
        not_contains = []
        not_contains_match = re.search(expected_not_contains_pattern, block)
        if not_contains_match:
            not_contains = [line.strip("- ").strip() for line in not_contains_match.group(1).strip().split("\n") if line.strip().startswith("-")]
        
        # Expected behavior (para LLM-as-judge)
        expected_behavior = ""
        behavior_match = re.search(expected_behavior_pattern, block, re.DOTALL)
        if behavior_match:
            expected_behavior = behavior_match.group(1).strip()
        
        test_cases.append(TestCase(
            name=name,
            prompt=prompt,
            expected_contains=contains,
            expected_not_contains=not_contains,
            expected_behavior=expected_behavior
        ))
    
    return test_cases


async def run_test_with_agent(
    client: CopilotClient,
    prompt: str,
    agent_config: dict | None = None,
    timeout: float = 120.0
) -> tuple[str, float, list[str]]:
    """
    Ejecuta un test con o sin agente personalizado.
    
    Args:
        client: Cliente de Copilot
        prompt: Prompt a enviar
        agent_config: Configuración del agente (None para baseline)
        timeout: Timeout en segundos
        
    Returns:
        Tuple con (respuesta_completa, latencia_ms, archivos_creados)
        La respuesta incluye mensajes del asistente + código de herramientas
    """
    session_config: dict[str, Any] = {
        "model": "gpt-5",
        "on_permission_request": lambda req, ctx: {"kind": "approved"},
    }
    
    if agent_config:
        session_config["custom_agents"] = [agent_config]
    
    session = await client.create_session(session_config)
    
    response_parts: list[str] = []
    created_files: list[str] = []
    done = asyncio.Event()
    
    def on_event(event):
        event_type = event.type.value
        
        # Capturar mensajes del asistente
        if event_type == "assistant.message" and event.data.content:
            response_parts.append(f"[MESSAGE]\n{event.data.content}")
        
        # Capturar código creado por herramientas
        elif event_type == "tool.execution_start":
            tool_name = event.data.tool_name or ""
            args = event.data.arguments or {}
            
            # Capturar código de herramientas create/edit y rastrear archivos
            if tool_name == "create":
                if "file_text" in args:
                    response_parts.append(f"[CODE:{tool_name}]\n{args.get('file_text', '')}")
                if "path" in args:
                    created_files.append(args["path"])
            elif tool_name == "edit" and "file_text" in args:
                response_parts.append(f"[CODE:{tool_name}]\n{args.get('file_text', '')}")
            elif tool_name == "bash" and "command" in args:
                response_parts.append(f"[BASH]\n{args.get('command', '')}")
        
        # Capturar resultados de herramientas
        elif event_type == "tool.execution_complete":
            if event.data.result and event.data.result.content:
                response_parts.append(f"[RESULT]\n{event.data.result.content}")
        
        elif event_type in {"session.idle", "session.error"}:
            done.set()
    
    session.on(on_event)
    
    start_time = time.time()
    
    try:
        # Si hay agente, prefijamos con @agent_name
        full_prompt = prompt
        if agent_config:
            full_prompt = f"@{agent_config['name']} {prompt}"
        
        await session.send({"prompt": full_prompt})
        await asyncio.wait_for(done.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        response_parts.append("[TIMEOUT]")
    finally:
        latency_ms = (time.time() - start_time) * 1000
        await session.destroy()
    
    # Combinar todas las partes
    full_response = "\n\n".join(response_parts)
    return full_response, latency_ms, created_files


def evaluate_response(
    response: str,
    expected_contains: list[str],
    expected_not_contains: list[str]
) -> tuple[list[str], list[str], list[str], list[str]]:
    """
    Evalúa si la respuesta cumple con las expectativas.
    
    Returns:
        Tuple con (contains_passed, contains_failed, not_contains_passed, not_contains_failed)
    """
    response_lower = response.lower()
    
    contains_passed = []
    contains_failed = []
    
    for expected in expected_contains:
        if expected.lower() in response_lower:
            contains_passed.append(expected)
        else:
            contains_failed.append(expected)
    
    not_contains_passed = []
    not_contains_failed = []
    
    for forbidden in expected_not_contains:
        if forbidden.lower() not in response_lower:
            not_contains_passed.append(forbidden)
        else:
            not_contains_failed.append(forbidden)
    
    return contains_passed, contains_failed, not_contains_passed, not_contains_failed


async def evaluate_with_llm(
    client: CopilotClient,
    test_name: str,
    prompt: str,
    response: str,
    expected_behavior: str,
    timeout: float = 30.0
) -> tuple[float, bool, str]:
    """
    Evalúa la respuesta usando Copilot como juez (LLM-as-judge).
    
    Args:
        client: Cliente de Copilot
        test_name: Nombre del test
        prompt: Prompt original enviado
        response: Respuesta del agente
        expected_behavior: Descripción del comportamiento esperado
        timeout: Timeout en segundos
        
    Returns:
        Tuple con (score 0-100, passed, reasoning)
    """
    # Si no hay expected_behavior, no podemos evaluar con LLM
    if not expected_behavior:
        return 0.0, False, "No hay expected_behavior definido para evaluación LLM"
    
    judge_prompt = f"""Eres un evaluador experto de código y respuestas de IA. Tu tarea es evaluar si una respuesta cumple con el comportamiento esperado.

## Test: {test_name}

## Prompt Original
{prompt}

## Comportamiento Esperado
{expected_behavior}

## Respuesta del Agente
{response[:2000]}

## Instrucciones de Evaluación
Evalúa la respuesta considerando:
1. ¿El código generado cumple con los requisitos funcionales esperados?
2. ¿La lógica y estructura del código son correctas?
3. ¿Sigue los patrones y prácticas mencionadas en el comportamiento esperado?

## IMPORTANTE - Criterios de Tolerancia:
- Si la respuesta está TRUNCADA pero el código visible es correcto, evalúa lo que hay disponible favorablemente
- Las tareas LLM son complejas y pueden tener latencia alta - esto es NORMAL y no debe penalizarse
- Enfócate en si el código FUNCIONA y cumple el propósito, no en aspectos cosméticos
- Si los keywords esperados están presentes y el código es funcional, considera pasar el test

## Formato de Respuesta (OBLIGATORIO)
Responde EXACTAMENTE en este formato JSON:
{{
    "score": <número 0-100>,
    "passed": <true/false>,
    "reasoning": "<explicación en 1-2 frases>"
}}

- score: 0-100 donde 100 es perfecto
- passed: true si score >= 70
- reasoning: explicación breve del juicio

Responde SOLO con el JSON, sin texto adicional."""

    session = await client.create_session({"model": "gpt-5"})
    
    done = asyncio.Event()
    llm_response = ""
    
    def on_event(event):
        nonlocal llm_response
        if event.type.value == "assistant.message" and event.data.content:
            llm_response = event.data.content
        elif event.type.value in {"session.idle", "session.error"}:
            done.set()
    
    session.on(on_event)
    
    try:
        await session.send({"prompt": judge_prompt})
        await asyncio.wait_for(done.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        return 50.0, False, "Timeout en evaluación LLM"
    finally:
        await session.destroy()
    
    # Parsear respuesta JSON
    try:
        # Limpiar posibles markdown code blocks
        clean_response = llm_response.strip()
        if clean_response.startswith("```"):
            clean_response = re.sub(r"```(?:json)?\n?", "", clean_response)
            clean_response = clean_response.rstrip("`").strip()
        
        result = json.loads(clean_response)
        score = float(result.get("score", 50))
        passed = bool(result.get("passed", score >= 70))
        reasoning = str(result.get("reasoning", "Sin explicación"))
        
        return score, passed, reasoning
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Si no puede parsear, intentar extraer score con regex
        score_match = re.search(r'"score"\s*:\s*(\d+)', llm_response)
        if score_match:
            score = float(score_match.group(1))
            return score, score >= 70, f"Evaluación parcial: {llm_response[:100]}"
        return 50.0, False, f"Error parseando respuesta LLM: {str(e)}"


async def validate_agent(
    agent_file: Path,
    compare_baseline: bool = True,
    verbose: bool = True
) -> ValidationReport:
    """
    Valida un agente ejecutando todos sus test cases.
    
    Args:
        agent_file: Ruta al archivo markdown del agente
        compare_baseline: Si comparar con el agente base
        verbose: Si imprimir progreso
        
    Returns:
        ValidationReport con todos los resultados
    """
    # Parsear definición
    agent_def = parse_agent_markdown(agent_file)
    
    if verbose:
        print("=" * 60)
        print(f"🔍 VALIDANDO AGENTE: {agent_def.display_name}")
        print(f"   Nombre: {agent_def.name}")
        print(f"   Tests: {len(agent_def.test_cases)}")
        print("=" * 60)
    
    # Crear cliente
    client = CopilotClient()
    await client.start()
    
    results: list[TestResult] = []
    baseline_results: dict[str, tuple[str, float]] = {}
    all_created_files: list[str] = []
    
    # Configuración del agente
    agent_config = {
        "name": agent_def.name,
        "display_name": agent_def.display_name,
        "description": agent_def.description,
        "prompt": agent_def.prompt,
        "tools": agent_def.tools if agent_def.tools else None,
    }
    
    try:
        for i, test in enumerate(agent_def.test_cases, 1):
            if verbose:
                print(f"\n📋 Test {i}/{len(agent_def.test_cases)}: {test.name}")
                print(f"   Prompt: {test.prompt[:50]}...")
            
            # Ejecutar con agente
            response, latency, created_files = await run_test_with_agent(
                client, test.prompt, agent_config
            )
            all_created_files.extend(created_files)
            
            # Ejecutar baseline si se solicita
            if compare_baseline:
                baseline_response, baseline_latency, baseline_files = await run_test_with_agent(
                    client, test.prompt, None
                )
                baseline_results[test.name] = (baseline_response, baseline_latency)
                all_created_files.extend(baseline_files)
            
            # Evaluar con keywords
            contains_passed, contains_failed, not_contains_passed, not_contains_failed = evaluate_response(
                response, test.expected_contains, test.expected_not_contains
            )
            
            keyword_passed = len(contains_failed) == 0 and len(not_contains_failed) == 0
            
            # Evaluar con LLM-as-judge si hay expected_behavior
            llm_score = 0.0
            llm_passed = False
            llm_reasoning = ""
            
            if test.expected_behavior:
                if verbose:
                    print(f"   🤖 Evaluando con LLM-as-judge...")
                llm_score, llm_passed, llm_reasoning = await evaluate_with_llm(
                    client, test.name, test.prompt, response, test.expected_behavior
                )
                if verbose:
                    llm_status = "✅" if llm_passed else "❌"
                    print(f"   {llm_status} LLM Score: {llm_score:.0f}/100 - {llm_reasoning[:60]}...")
            
            # El test pasa si cumple keywords Y (no hay LLM o LLM pasa)
            passed = keyword_passed and (not test.expected_behavior or llm_passed)
            
            result = TestResult(
                test_name=test.name,
                passed=passed,
                response=response,
                latency_ms=latency,
                contains_passed=contains_passed,
                contains_failed=contains_failed,
                not_contains_passed=not_contains_passed,
                not_contains_failed=not_contains_failed,
                llm_score=llm_score,
                llm_passed=llm_passed,
                llm_reasoning=llm_reasoning
            )
            results.append(result)
            
            if verbose:
                status = "✅ PASSED" if passed else "❌ FAILED"
                print(f"   {status} (latencia: {latency:.0f}ms)")
                if contains_failed:
                    print(f"   ⚠️  Falta: {contains_failed}")
                if not_contains_failed:
                    print(f"   ⚠️  Prohibido encontrado: {not_contains_failed}")
    
    finally:
        await client.stop()
    
    # Calcular estadísticas
    passed_count = sum(1 for r in results if r.passed)
    avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0
    
    # Calcular score (0-100)
    # Nueva fórmula con LLM:
    # - 40% tests pasados (keywords)
    # - 25% evaluación LLM (si hay expected_behavior)
    # - 15% latencia
    # - 20% seguridad
    
    success_rate = (passed_count / len(results)) if results else 0
    
    # Score LLM promedio (solo tests con expected_behavior)
    llm_tests = [r for r in results if r.llm_score > 0]
    llm_avg_score = sum(r.llm_score for r in llm_tests) / len(llm_tests) / 100 if llm_tests else 1.0
    
    # Penalización por violaciones de seguridad (expected_not_contains fallidos)
    security_violations = sum(len(r.not_contains_failed) for r in results)
    security_score = max(0, 1 - (security_violations * 0.25))  # -25% por cada violación
    
    # Latencia score (baseline como referencia)
    latency_score = 1.0
    if compare_baseline and baseline_results:
        baseline_avg = sum(b[1] for b in baseline_results.values()) / len(baseline_results)
        if baseline_avg > 0:
            latency_ratio = avg_latency / baseline_avg
            # Si es 1x = 100%, 2x = 50%, 3x = 33%, etc.
            latency_score = min(1.0, 1.0 / latency_ratio) if latency_ratio > 0 else 1.0
    
    # Calcular score final
    # Nota: La latencia tiene peso reducido (10%) porque las tareas LLM complejas
    # naturalmente requieren más tiempo y no deberían penalizarse excesivamente
    if llm_tests:
        # Con evaluación LLM
        score = round((success_rate * 40) + (llm_avg_score * 30) + (latency_score * 10) + (security_score * 20), 1)
    else:
        # Sin evaluación LLM (mantener fórmula original)
        score = round((success_rate * 60) + (latency_score * 20) + (security_score * 20), 1)
    
    # Comparación con baseline
    baseline_comparison = None
    if compare_baseline and baseline_results:
        baseline_comparison = {
            "latency_diff_avg_ms": avg_latency - (sum(b[1] for b in baseline_results.values()) / len(baseline_results)),
            "baseline_results": {name: {"response_preview": resp[:100], "latency_ms": lat} 
                                for name, (resp, lat) in baseline_results.items()}
        }
    
    report = ValidationReport(
        agent_name=agent_def.name,
        total_tests=len(results),
        passed_tests=passed_count,
        failed_tests=len(results) - passed_count,
        avg_latency_ms=avg_latency,
        score=score,
        results=results,
        created_files=list(set(all_created_files)),  # Eliminar duplicados
        baseline_comparison=baseline_comparison
    )
    
    if verbose:
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE VALIDACIÓN")
        print("=" * 60)
        print(f"   Agente: {agent_def.display_name}")
        print(f"   Tests pasados: {passed_count}/{len(results)}")
        print(f"   Tests fallidos: {len(results) - passed_count}/{len(results)}")
        print(f"   Latencia promedio: {avg_latency:.0f}ms")
        print(f"   Score: {score}/100")
        
        if baseline_comparison:
            diff = baseline_comparison["latency_diff_avg_ms"]
            diff_str = f"+{diff:.0f}ms" if diff > 0 else f"{diff:.0f}ms"
            print(f"   Diferencia vs baseline: {diff_str}")
        
        if score >= 80:
            print(f"\n   ✅ AGENTE VALIDADO (Score: {score})")
        elif score >= 50:
            print(f"\n   ⚠️  AGENTE CON PROBLEMAS (Score: {score})")
        else:
            print(f"\n   ❌ AGENTE FALLIDO (Score: {score})")
        
        print("=" * 60)
    
    return report


def cleanup_generated_files(files: list[str], verbose: bool = True) -> int:
    """
    Elimina los archivos generados durante las pruebas.
    
    Args:
        files: Lista de rutas de archivos a eliminar
        verbose: Si imprimir progreso
        
    Returns:
        Número de archivos eliminados
    """
    deleted = 0
    for file_path in files:
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                deleted += 1
                if verbose:
                    print(f"   🗑️  Eliminado: {file_path}")
        except Exception as e:
            if verbose:
                print(f"   ⚠️  Error eliminando {file_path}: {e}")
    return deleted


def load_previous_report(report_file: Path) -> dict | None:
    """
    Carga el reporte JSON anterior si existe.
    
    Args:
        report_file: Ruta al archivo JSON del reporte
        
    Returns:
        Dict con el reporte anterior o None si no existe
    """
    if not report_file.exists():
        return None
    
    try:
        content = report_file.read_text(encoding="utf-8")
        return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️  Error leyendo reporte anterior: {e}")
        return None


def compare_reports(
    current: ValidationReport,
    previous: dict | None,
    regression_threshold: float = 5.0
) -> HistoricalComparison | None:
    """
    Compara el reporte actual con el anterior para detectar regresiones.
    
    Args:
        current: Reporte de validación actual
        previous: Reporte anterior (dict desde JSON)
        regression_threshold: Diferencia mínima de score para considerar regresión
        
    Returns:
        HistoricalComparison o None si no hay reporte anterior
    """
    if previous is None:
        return None
    
    # Extraer valores del reporte anterior
    prev_score = previous.get("score", 0)
    prev_passed = previous.get("passed_tests", 0)
    prev_latency = previous.get("avg_latency_ms", 0)
    prev_results = {r["test_name"]: r["passed"] for r in previous.get("results", [])}
    
    # Calcular diferencias
    score_diff = current.score - prev_score
    passed_diff = current.passed_tests - prev_passed
    latency_diff = current.avg_latency_ms - prev_latency
    
    # Detectar regresiones (tests que antes pasaban y ahora fallan)
    regressions = []
    improvements = []
    
    for result in current.results:
        test_name = result.test_name
        current_passed = result.passed
        prev_passed_test = prev_results.get(test_name)
        
        if prev_passed_test is not None:
            if prev_passed_test and not current_passed:
                regressions.append(test_name)
            elif not prev_passed_test and current_passed:
                improvements.append(test_name)
    
    # Determinar si es una regresión significativa
    is_regression = score_diff < -regression_threshold or len(regressions) > 0
    
    return HistoricalComparison(
        previous_score=prev_score,
        current_score=current.score,
        score_diff=score_diff,
        previous_passed=prev_passed,
        current_passed=current.passed_tests,
        passed_diff=passed_diff,
        previous_latency=prev_latency,
        current_latency=current.avg_latency_ms,
        latency_diff=latency_diff,
        regressions=regressions,
        improvements=improvements,
        is_regression=is_regression
    )


def print_historical_comparison(comparison: HistoricalComparison, verbose: bool = True):
    """
    Imprime la comparación histórica en consola.
    
    Args:
        comparison: Comparación con ejecución anterior
        verbose: Si imprimir detalles
    """
    if not verbose:
        return
    
    print("\n" + "=" * 60)
    print("📈 COMPARACIÓN HISTÓRICA")
    print("=" * 60)
    
    # Score
    score_icon = "📈" if comparison.score_diff > 0 else "📉" if comparison.score_diff < 0 else "➡️"
    score_str = f"+{comparison.score_diff:.1f}" if comparison.score_diff > 0 else f"{comparison.score_diff:.1f}"
    print(f"   {score_icon} Score: {comparison.previous_score:.1f} → {comparison.current_score:.1f} ({score_str})")
    
    # Tests pasados
    passed_icon = "📈" if comparison.passed_diff > 0 else "📉" if comparison.passed_diff < 0 else "➡️"
    passed_str = f"+{comparison.passed_diff}" if comparison.passed_diff > 0 else f"{comparison.passed_diff}"
    print(f"   {passed_icon} Tests pasados: {comparison.previous_passed} → {comparison.current_passed} ({passed_str})")
    
    # Latencia
    latency_icon = "📈" if comparison.latency_diff < 0 else "📉" if comparison.latency_diff > 0 else "➡️"
    latency_str = f"+{comparison.latency_diff:.0f}ms" if comparison.latency_diff > 0 else f"{comparison.latency_diff:.0f}ms"
    print(f"   {latency_icon} Latencia: {comparison.previous_latency:.0f}ms → {comparison.current_latency:.0f}ms ({latency_str})")
    
    # Regresiones
    if comparison.regressions:
        print(f"\n   🔴 REGRESIONES DETECTADAS ({len(comparison.regressions)}):")
        for test in comparison.regressions:
            print(f"      ❌ {test} (antes pasaba, ahora falla)")
    
    # Mejoras
    if comparison.improvements:
        print(f"\n   🟢 MEJORAS ({len(comparison.improvements)}):")
        for test in comparison.improvements:
            print(f"      ✅ {test} (antes fallaba, ahora pasa)")
    
    # Veredicto final
    print()
    if comparison.is_regression:
        print("   ⚠️  ALERTA: Se detectaron regresiones en el agente")
    elif comparison.score_diff > 0:
        print("   ✅ El agente ha mejorado respecto a la versión anterior")
    elif comparison.score_diff == 0 and not comparison.regressions:
        print("   ➡️  Sin cambios significativos respecto a la versión anterior")
    
    print("=" * 60)


def save_historical_report(
    agent_file: Path,
    report_dict: dict,
    comparison: HistoricalComparison | None
) -> Path:
    """
    Guarda el reporte con histórico en un archivo separado.
    
    Args:
        agent_file: Archivo del agente
        report_dict: Reporte actual como dict
        comparison: Comparación histórica
        
    Returns:
        Path del archivo histórico guardado
    """
    history_dir = agent_file.parent / "history"
    history_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = history_dir / f"{agent_file.stem}_{timestamp}.json"
    
    # Agregar comparación al reporte
    report_with_history = report_dict.copy()
    report_with_history["timestamp"] = datetime.now().isoformat()
    
    if comparison:
        report_with_history["historical_comparison"] = {
            "previous_score": comparison.previous_score,
            "score_diff": comparison.score_diff,
            "regressions": comparison.regressions,
            "improvements": comparison.improvements,
            "is_regression": comparison.is_regression
        }
    
    history_file.write_text(json.dumps(report_with_history, indent=2, ensure_ascii=False))
    return history_file


async def generate_markdown_report(
    report: ValidationReport,
    agent_def: AgentDefinition,
    client: CopilotClient,
    comparison: HistoricalComparison | None = None
) -> str:
    """
    Genera un reporte en Markdown utilizando Copilot para análisis.
    
    Args:
        report: Reporte de validación
        agent_def: Definición del agente
        client: Cliente de Copilot
        comparison: Comparación histórica (opcional)
        
    Returns:
        Contenido del reporte en Markdown
    """
    # Preparar resumen de resultados para Copilot
    failed_tests_info = []
    for r in report.results:
        if not r.passed:
            failed_tests_info.append({
                "test": r.test_name,
                "missing": r.contains_failed,
                "forbidden_found": r.not_contains_failed,
                "response_preview": r.response[:300] if r.response else ""
            })
    
    analysis_prompt = f"""
Analiza los siguientes resultados de validación de un agente personalizado y genera un reporte técnico.

## Información del Agente
- Nombre: {agent_def.name}
- Descripción: {agent_def.description}
- Prompt del agente (primeras 500 chars): {agent_def.prompt[:500]}...

## Resultados de Validación
- Tests totales: {report.total_tests}
- Tests pasados: {report.passed_tests}
- Tests fallidos: {report.failed_tests}
- Score: {report.score}/100
- Latencia promedio: {report.avg_latency_ms:.0f}ms

## Tests Fallidos
{failed_tests_info}

## Instrucciones
Genera un análisis en formato Markdown con las siguientes secciones:
1. **Resumen Ejecutivo** - Evaluación general del agente (2-3 frases)
2. **Errores Detectados** - Lista detallada de cada error encontrado
3. **Análisis de Seguridad** - Si hubo violaciones de restricciones (expected_not_contains)
4. **Conclusiones** - Puntos fuertes y débiles del agente
5. **Recomendaciones** - Cómo corregir cada problema específico del prompt del agente
6. **Score Final** - Justificación del score {report.score}/100

Sé específico y técnico. Responde SOLO con el Markdown, sin explicaciones adicionales.
"""

    session = await client.create_session({"model": "gpt-5"})
    
    done = asyncio.Event()
    analysis_content = ""
    
    def on_event(event):
        nonlocal analysis_content
        if event.type.value == "assistant.message" and event.data.content:
            analysis_content = event.data.content
        elif event.type.value in {"session.idle", "session.error"}:
            done.set()
    
    session.on(on_event)
    
    try:
        await session.send({"prompt": analysis_prompt})
        await asyncio.wait_for(done.wait(), timeout=60)
    except asyncio.TimeoutError:
        analysis_content = "Error: Timeout generando análisis"
    finally:
        await session.destroy()
    
    # Construir reporte final
    markdown = f"""# Reporte de Validación: {agent_def.display_name}

**Fecha:** {time.strftime("%Y-%m-%d %H:%M:%S")}  
**Agente:** `{agent_def.name}`  
**Score:** {report.score}/100 {"✅" if report.score >= 80 else "⚠️" if report.score >= 50 else "❌"}

---

## 📊 Métricas

| Métrica | Valor |
|---------|-------|
| Tests Totales | {report.total_tests} |
| Tests Pasados | {report.passed_tests} |
| Tests Fallidos | {report.failed_tests} |
| Tasa de Éxito | {(report.passed_tests/report.total_tests*100):.1f}% |
| Latencia Promedio | {report.avg_latency_ms:.0f}ms |
| Score Final | **{report.score}/100** |

---

## 📋 Resultados por Test

| Test | Estado | LLM Score | Latencia | Problemas |
|------|--------|-----------|----------|-----------|
"""
    
    for r in report.results:
        status = "✅" if r.passed else "❌"
        llm_score_str = f"{r.llm_score:.0f}/100" if r.llm_score > 0 else "-"
        problems = []
        if r.contains_failed:
            problems.append(f"Falta: {', '.join(r.contains_failed)}")
        if r.not_contains_failed:
            problems.append(f"🔴 Prohibido: {', '.join(r.not_contains_failed)}")
        if r.llm_score > 0 and not r.llm_passed:
            problems.append(f"LLM: {r.llm_reasoning[:40]}...")
        problems_str = "; ".join(problems) if problems else "-"
        markdown += f"| {r.test_name} | {status} | {llm_score_str} | {r.latency_ms:.0f}ms | {problems_str} |\n"
    
    # Añadir sección de evaluación LLM detallada si hay tests con LLM
    llm_tests = [r for r in report.results if r.llm_score > 0]
    if llm_tests:
        markdown += """
---

## 🧠 Evaluación LLM-as-Judge

"""
        for r in llm_tests:
            llm_status = "✅" if r.llm_passed else "❌"
            markdown += f"### {r.test_name} {llm_status}\n"
            markdown += f"- **Score**: {r.llm_score:.0f}/100\n"
            markdown += f"- **Veredicto**: {'Aprobado' if r.llm_passed else 'Rechazado'}\n"
            markdown += f"- **Razonamiento**: {r.llm_reasoning}\n\n"
    
    markdown += f"""
---

## 🤖 Análisis de Copilot

{analysis_content}

---

## 📁 Archivos Generados en Tests

Se generaron **{len(report.created_files)}** archivos durante las pruebas:

"""
    
    if report.created_files:
        for f in report.created_files:
            markdown += f"- `{f}` (eliminado)\n"
    else:
        markdown += "- Ninguno\n"
    
    # Agregar sección de comparación histórica si existe
    if comparison:
        score_icon = "📈" if comparison.score_diff > 0 else "📉" if comparison.score_diff < 0 else "➡️"
        score_str = f"+{comparison.score_diff:.1f}" if comparison.score_diff > 0 else f"{comparison.score_diff:.1f}"
        
        markdown += f"""
---

## 📈 Comparación Histórica

| Métrica | Anterior | Actual | Diferencia |
|---------|----------|--------|------------|
| Score | {comparison.previous_score:.1f} | {comparison.current_score:.1f} | {score_icon} {score_str} |
| Tests Pasados | {comparison.previous_passed} | {comparison.current_passed} | {'+' if comparison.passed_diff > 0 else ''}{comparison.passed_diff} |
| Latencia | {comparison.previous_latency:.0f}ms | {comparison.current_latency:.0f}ms | {'+' if comparison.latency_diff > 0 else ''}{comparison.latency_diff:.0f}ms |

"""
        
        if comparison.regressions:
            markdown += "### 🔴 Regresiones Detectadas\n\n"
            for test in comparison.regressions:
                markdown += f"- **{test}** - Antes pasaba, ahora falla\n"
            markdown += "\n"
        
        if comparison.improvements:
            markdown += "### 🟢 Mejoras\n\n"
            for test in comparison.improvements:
                markdown += f"- **{test}** - Antes fallaba, ahora pasa\n"
            markdown += "\n"
        
        if comparison.is_regression:
            markdown += "> ⚠️ **ALERTA**: Se detectaron regresiones en el agente. Revisar cambios recientes.\n"
        elif comparison.score_diff > 0:
            markdown += "> ✅ El agente ha mejorado respecto a la versión anterior.\n"
    
    markdown += """
---

*Reporte generado automáticamente por Agent Validator*
"""
    
    return markdown


async def main():
    """Punto de entrada principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validador de Custom Agents para Copilot SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python agent_validator.py agents/python_expert.md
  python agent_validator.py agents/sql_expert.md --threshold 80
  python agent_validator.py agents/devops.md --llm-judge true --output report.json
        """
    )
    parser.add_argument(
        "agent_file",
        nargs="?",
        default="agents/python_expert.md",
        help="Ruta al archivo del agente (.md)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=70.0,
        help="Score mínimo para pasar el Quality Gate (default: 70)"
    )
    parser.add_argument(
        "--llm-judge",
        type=str,
        default="true",
        help="Activar evaluación LLM-as-judge (true/false)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Ruta para guardar el reporte JSON (default: <agent>.report.json)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Mostrar salida detallada"
    )
    
    args = parser.parse_args()
    
    agent_file = Path(args.agent_file)
    threshold = args.threshold
    enable_llm_judge = args.llm_judge.lower() == "true"
    output_file = Path(args.output) if args.output else None
    verbose = args.verbose
    
    if not agent_file.exists():
        print(f"❌ Archivo no encontrado: {agent_file}")
        return 1
    
    # Cargar reporte anterior si existe
    report_json_file = agent_file.with_suffix(".report.json")
    previous_report = load_previous_report(report_json_file)
    
    if previous_report:
        print(f"📂 Reporte anterior encontrado (score: {previous_report.get('score', 'N/A')})")
    else:
        print("📂 Sin reporte anterior - primera ejecución")
    
    # Validar agente
    report = await validate_agent(agent_file, compare_baseline=True, verbose=True)
    
    # Comparar con ejecución anterior
    comparison = compare_reports(report, previous_report)
    
    if comparison:
        print_historical_comparison(comparison, verbose=True)
    
    # Parsear definición para el reporte
    agent_def = parse_agent_markdown(agent_file)
    
    # Limpiar archivos generados
    if report.created_files:
        print(f"\n🧹 Limpiando {len(report.created_files)} archivos generados...")
        deleted = cleanup_generated_files(report.created_files, verbose=True)
        print(f"   Total eliminados: {deleted}")
    
    # Generar reporte Markdown con Copilot
    print("\n📝 Generando reporte con análisis de Copilot...")
    client = CopilotClient()
    await client.start()
    
    try:
        markdown_report = await generate_markdown_report(report, agent_def, client, comparison)
    finally:
        await client.stop()
    
    # Guardar reporte Markdown
    report_md_file = agent_file.with_suffix(".report.md")
    report_md_file.write_text(markdown_report, encoding="utf-8")
    print(f"📄 Reporte Markdown guardado en: {report_md_file}")
    
    # Preparar reporte JSON
    report_dict = {
        "agent_name": report.agent_name,
        "total_tests": report.total_tests,
        "passed_tests": report.passed_tests,
        "failed_tests": report.failed_tests,
        "avg_latency_ms": report.avg_latency_ms,
        "score": report.score,
        "success_rate": (report.passed_tests / report.total_tests * 100) if report.total_tests > 0 else 0,
        "timestamp": report.timestamp,
        "results": [
            {
                "test_name": r.test_name,
                "passed": r.passed,
                "latency_ms": r.latency_ms,
                "response_preview": r.response[:200] if r.response else "",
                "contains_failed": r.contains_failed,
                "not_contains_failed": r.not_contains_failed,
                "llm_score": r.llm_score,
                "llm_passed": r.llm_passed,
                "llm_reasoning": r.llm_reasoning
            }
            for r in report.results
        ],
        "created_files": report.created_files,
        "baseline_comparison": report.baseline_comparison,
        "threshold": threshold,
        "quality_gate_passed": report.score >= threshold
    }
    
    # Guardar reporte JSON (usar --output si se especifica)
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(report_dict, indent=2, ensure_ascii=False))
        print(f"📄 Reporte JSON guardado en: {output_file}")
    else:
        report_json_file.write_text(json.dumps(report_dict, indent=2, ensure_ascii=False))
        print(f"📄 Reporte JSON guardado en: {report_json_file}")
    
    # Guardar histórico con timestamp
    history_file = save_historical_report(agent_file, report_dict, comparison)
    print(f"📜 Histórico guardado en: {history_file}")
    
    # Mostrar resultado final y Quality Gate
    print(f"\n🎯 Score Final: {report.score}/100")
    print(f"📊 Threshold: {threshold}")
    
    if report.score >= threshold:
        print(f"✅ QUALITY GATE PASSED (score >= {threshold})")
    else:
        print(f"❌ QUALITY GATE FAILED (score < {threshold})")
    
    if comparison:
        if comparison.is_regression:
            print("⚠️  REGRESIÓN DETECTADA - Revisar cambios en el agente")
        elif comparison.score_diff > 0:
            print(f"📈 Mejora de {comparison.score_diff:.1f} puntos respecto a la versión anterior")
    
    # Exit code basado en Quality Gate
    if report.score < threshold:
        return 1
    return 0


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code if exit_code else 0)
