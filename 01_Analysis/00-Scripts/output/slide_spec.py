"""YAML-driven slide specification loader and renderer.

A slide spec is data: action title template, callout text, footer line, and
inputs that resolve against ctx.results. The renderer walks the spec, fills
templates from ctx, and returns SlideContent that deck_builder can lay out.

Specs live in docs/slide_specs/<section>.yml. Each spec keyed by slide_id.
This decouples slide copy from analytics code -- product/design changes the
spec, the analytics doesn't recompile.

Spec schema (per slide):

    SLIDE_ID:
      layout: TWO_CONTENT          # one of LAYOUTS in deck_builder
      components: [A7.6a, DCTR-7]  # chart ids contributing to this slide
      action_title: "L12M DCTR of {l12m_rate:.0%} {direction} ..."
      inputs:                      # dotted-path resolvers against ctx.results
        l12m_rate: ctx.results.dctr_3.insights.dctr
        direction: "trails if gap_pp<0 else beats"  # expression -- evaluated
      denominator_label: Eligible  # ties Wave 1 law to this slide
      callout:
        hero: "${delta_revenue:,.1f}M"
        sub:  "annual debit interchange uplift"
        tertiary: "Closing the gap at {b1}, {b2}, {b3}"
      footer:
        source: "Source: {client_name} ODD, {month} | N = {eligible_count:,}"

Wave 3 wires render_spec into deck_builder._result_to_slide as an opt-in
fallback: when a spec exists for a slide_id, render from it; otherwise keep
today's behavior. Zero-risk rollout, spec by spec.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML pinned in requirements
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass
class CalloutSpec:
    hero: str = ""
    sub: str = ""
    tertiary: str = ""


@dataclass
class FooterSpec:
    source: str = ""
    confidentiality: str = "Confidential — for internal CSM/client use only"


@dataclass
class SlideSpec:
    slide_id: str = ""
    layout: str = "TWO_CONTENT"
    components: list[str] = field(default_factory=list)
    action_title: str = ""
    inputs: dict[str, str] = field(default_factory=dict)
    denominator_label: str = ""
    callout: CalloutSpec = field(default_factory=CalloutSpec)
    footer: FooterSpec = field(default_factory=FooterSpec)


@dataclass
class SlideContent:
    """Rendered output the deck builder consumes."""

    slide_id: str = ""
    layout: str = "TWO_CONTENT"
    action_title: str = ""
    components: list[str] = field(default_factory=list)
    callout_hero: str = ""
    callout_sub: str = ""
    callout_tertiary: str = ""
    footer_source: str = ""
    footer_confidentiality: str = ""
    denominator_label: str = ""
    # If anything failed to resolve cleanly, populate this so the deck builder
    # can fall back gracefully and we log a precise reason.
    render_warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


_DEFAULT_SPECS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "docs" / "slide_specs"
)


def specs_dir() -> Path:
    """Return the directory to load specs from. Override with SLIDE_SPECS_DIR."""
    env = os.environ.get("SLIDE_SPECS_DIR")
    if env:
        return Path(env)
    return _DEFAULT_SPECS_DIR


def _parse_spec_dict(slide_id: str, raw: dict) -> SlideSpec:
    callout = raw.get("callout") or {}
    footer = raw.get("footer") or {}
    return SlideSpec(
        slide_id=slide_id,
        layout=raw.get("layout", "TWO_CONTENT"),
        components=list(raw.get("components") or []),
        action_title=raw.get("action_title", ""),
        inputs=dict(raw.get("inputs") or {}),
        denominator_label=raw.get("denominator_label", ""),
        callout=CalloutSpec(
            hero=callout.get("hero", ""),
            sub=callout.get("sub", ""),
            tertiary=callout.get("tertiary", ""),
        ),
        footer=FooterSpec(
            source=footer.get("source", ""),
            confidentiality=footer.get(
                "confidentiality",
                "Confidential — for internal CSM/client use only",
            ),
        ),
    )


def load_specs(section: str) -> dict[str, SlideSpec]:
    """Parse docs/slide_specs/<section>.yml into a {slide_id: SlideSpec} map.

    Returns an empty dict if the file is missing, PyYAML is unavailable, or the
    YAML is empty. Never raises; failures log a warning.
    """
    if yaml is None:
        logger.warning("slide_spec: PyYAML not installed; specs disabled")
        return {}

    path = specs_dir() / f"{section}.yml"
    if not path.exists():
        return {}

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        logger.warning("slide_spec: failed to parse {p}: {err}", p=path, err=exc)
        return {}

    out: dict[str, SlideSpec] = {}
    for slide_id, body in raw.items():
        if not isinstance(body, dict):
            continue
        out[str(slide_id)] = _parse_spec_dict(str(slide_id), body)
    logger.info("slide_spec: loaded {n} spec(s) for section {s}", n=len(out), s=section)
    return out


# Cache so we don't re-parse a YAML file per slide.
_SPEC_CACHE: dict[str, dict[str, SlideSpec]] = {}


def get_spec(section: str, slide_id: str) -> SlideSpec | None:
    """Look up a single spec, loading and caching the section file as needed.

    Two-step resolution:
      1. Exact match on `slide_id` (the common case).
      2. Pattern match against keys containing `{name}` placeholders. The first
         placeholder-keyed spec whose regex matches `slide_id` is returned with
         the captured value injected as an additional input (`name` -> match).
         Lets mailer.yml declare ONE template entry like `A13.{month}` that
         renders every per-month slide (A13.Jan26, A13.Feb26, ...).
    """
    if section not in _SPEC_CACHE:
        _SPEC_CACHE[section] = load_specs(section)
    cached = _SPEC_CACHE[section]
    if slide_id in cached:
        return cached[slide_id]

    # Pattern match: keys with {name} become regex (?P<name>[^.]+) etc.
    import re
    for key, template in cached.items():
        if "{" not in key:
            continue
        pattern_re, capture_names = _compile_pattern_key(key)
        m = pattern_re.match(slide_id)
        if m is None:
            continue
        # Clone the template and:
        # 1. Inject captured names as quoted-literal inputs (so the renderer
        #    treats them as strings, not as dotted paths).
        # 2. Substitute {name} -> captured value in every input expression so
        #    `ctx.results.monthly_summaries.{month}.total_mailed` resolves at
        #    spec-render time.
        captured = m.groupdict()
        merged_inputs: dict[str, str] = {}
        for name, captured_val in captured.items():
            merged_inputs[name] = f'"{captured_val}"'
        for input_name, expr in template.inputs.items():
            substituted = str(expr)
            for cap_name, cap_val in captured.items():
                substituted = substituted.replace("{" + cap_name + "}", cap_val)
            merged_inputs[input_name] = substituted
        return SlideSpec(
            slide_id=slide_id,
            layout=template.layout,
            components=list(template.components),
            action_title=template.action_title,
            inputs=merged_inputs,
            denominator_label=template.denominator_label,
            callout=template.callout,
            footer=template.footer,
        )
    return None


def _compile_pattern_key(key: str) -> tuple["re.Pattern[str]", list[str]]:
    """Convert 'A13.{month}' to a compiled regex with named groups.

    Each `{name}` becomes `(?P<name>[^.]+)` so dots in the slide_id still act
    as path separators. Other characters are escaped.
    """
    import re
    pattern_chars: list[str] = []
    names: list[str] = []
    i = 0
    while i < len(key):
        ch = key[i]
        if ch == "{":
            end = key.find("}", i)
            if end == -1:
                pattern_chars.append(re.escape(ch))
                i += 1
                continue
            name = key[i + 1:end]
            names.append(name)
            # Capture only month-shaped tokens (e.g. "Apr26"): 3 letters + 2-4
            # digit year. A13.{month} is the sole placeholder-keyed spec; keeping
            # the capture tight stops non-month A13 slides (A13.5, A13.6, A13.Agg)
            # from matching and dragging in unresolved {overall_rate}/{total_*}
            # template tokens that then leak onto the slide.
            pattern_chars.append(rf"(?P<{name}>[A-Za-z]{{3}}\d{{2,4}})")
            i = end + 1
        else:
            pattern_chars.append(re.escape(ch))
            i += 1
    pattern = "^" + "".join(pattern_chars) + "$"
    return re.compile(pattern), names


def clear_spec_cache() -> None:
    _SPEC_CACHE.clear()


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def _resolve_dotted(path: str, ctx_results: dict[str, Any]) -> Any:
    """Resolve 'ctx.results.dctr_3.insights.dctr' against ctx_results.

    The leading 'ctx.results.' prefix is optional. Returns None if any step
    along the path is missing.
    """
    tokens = path.split(".")
    if tokens[:2] == ["ctx", "results"]:
        tokens = tokens[2:]
    cur: Any = ctx_results
    for tok in tokens:
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(tok)
        else:
            cur = getattr(cur, tok, None)
    return cur


_SAFE_BUILTINS = {
    "abs": abs, "min": min, "max": max, "round": round,
    "len": len, "int": int, "float": float, "str": str,
}


def _evaluate_input(expr: str, namespace: dict[str, Any]) -> Any:
    """Evaluate one inputs entry.

    Three flavors:
      - Dotted path resolving to ctx.results.* (returns the value).
      - Quoted literal (returns the string).
      - Python expression using already-resolved names in namespace.

    Restricted eval -- no builtins outside _SAFE_BUILTINS. Returns None on error.
    """
    expr = expr.strip()
    if not expr:
        return None
    # Bare dotted path against ctx.results
    if expr.startswith("ctx.") or expr.startswith("ctx.results"):
        return _resolve_dotted(expr, namespace.get("__ctx_results__", {}))
    # Quoted literal
    if (expr.startswith('"') and expr.endswith('"')) or (
        expr.startswith("'") and expr.endswith("'")
    ):
        return expr[1:-1]
    # Try treating as expression
    try:
        return eval(expr, {"__builtins__": _SAFE_BUILTINS}, namespace)
    except Exception as exc:
        logger.debug("slide_spec: input expression failed ({e}): {x}", e=exc, x=expr)
        return None


def _format(template: str, ns: dict[str, Any]) -> tuple[str, list[str]]:
    """Format `template` with the namespace; collect names that couldn't resolve."""
    warnings: list[str] = []

    class _Lenient(dict):
        def __missing__(self, key):  # type: ignore[override]
            warnings.append(f"missing input '{key}'")
            return "{" + key + "}"

    try:
        rendered = template.format_map(_Lenient(ns))
    except Exception as exc:
        warnings.append(f"format failed: {exc}")
        rendered = template
    return rendered, warnings


def render_spec(
    spec: SlideSpec,
    ctx_results: dict[str, Any],
    client_info: Any | None = None,
) -> SlideContent:
    """Resolve a spec against ctx.results and return rendered SlideContent.

    `client_info` is the ctx.client object; its public attributes (`client_name`,
    `month`, `client_id`) are exposed to the template namespace by name.
    """
    ns: dict[str, Any] = {"__ctx_results__": ctx_results}

    # Expose client metadata
    if client_info is not None:
        for attr in ("client_name", "month", "client_id", "csm"):
            if hasattr(client_info, attr):
                ns[attr] = getattr(client_info, attr)

    # Resolve inputs in declaration order so later expressions can use earlier ones
    warnings: list[str] = []
    for name, expr in spec.inputs.items():
        ns[name] = _evaluate_input(str(expr), ns)
        if ns[name] is None and name in str(spec.action_title):
            warnings.append(f"input '{name}' resolved to None")

    action_title, w1 = _format(spec.action_title, ns)
    hero, w2 = _format(spec.callout.hero, ns)
    sub, w3 = _format(spec.callout.sub, ns)
    tertiary, w4 = _format(spec.callout.tertiary, ns)
    source, w5 = _format(spec.footer.source, ns)
    warnings += w1 + w2 + w3 + w4 + w5

    # Defense in depth: never let an unresolved {token} reach a client slide.
    # If substitution failed, drop the callout/footer field rather than rendering
    # literal template code. action_title is left for the deck-side guard, which
    # falls back to a legacy title when braces remain.
    import re as _re
    _residual = _re.compile(r"\{[A-Za-z_][\w.]*(?::[^}]*)?\}")

    def _clean(text: str, field: str) -> str:
        if text and _residual.search(text):
            warnings.append(f"dropped {field}: unresolved template token in {text!r}")
            return ""
        return text

    hero = _clean(hero, "callout.hero")
    sub = _clean(sub, "callout.sub")
    tertiary = _clean(tertiary, "callout.tertiary")
    source = _clean(source, "footer.source")

    return SlideContent(
        slide_id=spec.slide_id,
        layout=spec.layout,
        action_title=action_title,
        components=list(spec.components),
        callout_hero=hero,
        callout_sub=sub,
        callout_tertiary=tertiary,
        footer_source=source,
        footer_confidentiality=spec.footer.confidentiality,
        denominator_label=spec.denominator_label,
        render_warnings=warnings,
    )
