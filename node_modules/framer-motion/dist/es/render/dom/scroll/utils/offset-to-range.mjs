import { ScrollOffset } from '../offsets/presets.mjs';

/**
 * Maps from ProgressIntersection pairs used by Motion's preset offsets to
 * ViewTimeline named ranges. Returns undefined for unrecognised patterns,
 * which signals the caller to fall back to JS-based scroll tracking.
 */
const presets = [
    [ScrollOffset.Enter, "entry"],
    [ScrollOffset.Exit, "exit"],
    [ScrollOffset.Any, "cover"],
    [ScrollOffset.All, "contain"],
];
function matchesPreset(offset, preset) {
    if (offset.length !== 2)
        return false;
    for (let i = 0; i < 2; i++) {
        const o = offset[i];
        const p = preset[i];
        if (!Array.isArray(o) ||
            o.length !== 2 ||
            o[0] !== p[0] ||
            o[1] !== p[1])
            return false;
    }
    return true;
}
function offsetToViewTimelineRange(offset) {
    if (!offset) {
        return { rangeStart: "contain 0%", rangeEnd: "contain 100%" };
    }
    for (const [preset, name] of presets) {
        if (matchesPreset(offset, preset)) {
            return { rangeStart: `${name} 0%`, rangeEnd: `${name} 100%` };
        }
    }
    return undefined;
}

export { offsetToViewTimelineRange };
//# sourceMappingURL=offset-to-range.mjs.map
