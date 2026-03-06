import { UnresolvedValueKeyframe, AnimationOptions, MotionValue, Transition, ElementOrSelector, DOMKeyframesDefinition, AnimationPlaybackOptions, GroupAnimationWithThen, AnimationPlaybackControlsWithThen } from 'motion-dom';

type ObjectTarget<O> = {
    [K in keyof O]?: O[K] | UnresolvedValueKeyframe[];
};
type SequenceTime = number | "<" | `+${number}` | `-${number}` | `${string}`;
type SequenceLabel = string;
interface SequenceLabelWithTime {
    name: SequenceLabel;
    at: SequenceTime;
}
interface At {
    at?: SequenceTime;
}
type MotionValueSegment = [
    MotionValue,
    UnresolvedValueKeyframe | UnresolvedValueKeyframe[]
];
type MotionValueSegmentWithTransition = [
    MotionValue,
    UnresolvedValueKeyframe | UnresolvedValueKeyframe[],
    Transition & At
];
type DOMSegment = [ElementOrSelector, DOMKeyframesDefinition];
type DOMSegmentWithTransition = [
    ElementOrSelector,
    DOMKeyframesDefinition,
    AnimationOptions & At
];
type ObjectSegment<O extends {} = {}> = [O, ObjectTarget<O>];
type ObjectSegmentWithTransition<O extends {} = {}> = [
    O,
    ObjectTarget<O>,
    AnimationOptions & At
];
type SequenceProgressCallback = (value: any) => void;
type FunctionSegment = [SequenceProgressCallback] | [SequenceProgressCallback, AnimationOptions & At] | [
    SequenceProgressCallback,
    UnresolvedValueKeyframe | UnresolvedValueKeyframe[],
    AnimationOptions & At
];
type Segment = ObjectSegment | ObjectSegmentWithTransition | SequenceLabel | SequenceLabelWithTime | MotionValueSegment | MotionValueSegmentWithTransition | DOMSegment | DOMSegmentWithTransition | FunctionSegment;
type AnimationSequence = Segment[];
interface SequenceOptions extends AnimationPlaybackOptions {
    delay?: number;
    duration?: number;
    defaultTransition?: Transition;
    reduceMotion?: boolean;
    onComplete?: () => void;
}

declare function animateSequence(definition: AnimationSequence, options?: SequenceOptions): GroupAnimationWithThen;

declare const animateMini: (elementOrSelector: ElementOrSelector, keyframes: DOMKeyframesDefinition, options?: AnimationOptions) => AnimationPlaybackControlsWithThen;

export { animateMini as animate, animateSequence };
