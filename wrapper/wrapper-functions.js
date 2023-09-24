
/**
 * @typedef SimulationStep
 * @property {string} type
 * 
 */

/**
 * 
 * @param {SimulationStep[]} steps 
 * @param {number} currentStep 
 * @param {"expression"} mode
 * @returns {number}
 */
export function stepForward(steps, currentStep, mode) {
    if (mode !== "expression")
        throw new error("Unsupported mode " + mode);

    return currentStep < steps.length - 1 ? currentStep + 1 : undefined;
}

/**
 * 
 * @param {SimulationStep[]} steps 
 * @param {number} currentStep 
 * @param {"expression"} mode
 * @returns {number}
 */
export function stepBackwards(steps, currentStep, mode) {
    if (mode !== "expression")
        throw new error("Unsupported mode " + mode);

    return currentStep > 0 ? currentStep - 1 : undefined;
}

/**
 * 
 * @param {string} code 
 * @param {SimulationStep[]} steps 
 */
export function getEvaluatedCode(code, steps) {
    // TODO implement clear for active-statement-change 

    // Filters out steps with encompased by other steps
    const expressionSteps = steps.filter(s => s.type === "expression");
    const activeExpressionSteps = expressionSteps.reduce(
        (steps, value) => [...steps.filter(s => !isLocationWithinLocation(s.location, value.location)), value],
        []
    );
    // Ordering steps according to start line and start charachter 
    activeExpressionSteps.sort(
        (s1, s2) => (s1.location[0] == s2.location[0]) ?  s1.location[1] - s2.location[1] : s1.location[0] - s2.location[0]
    );

    return getEvaluatedCodeInternal(code, activeExpressionSteps);
}

// Calculates evaluated code from a list of ordered non-overlapping steps
function getEvaluatedCodeInternal(code, activeSteps) {
    let buffer = "";

    for(let i = 0; i < activeSteps.length; i++) {
        const step = activeSteps[i];
        const nextStep = (i < activeSteps.length - 1) ? activeSteps[i + 1] : undefined;

        if (i == 0) buffer += getContentBeforeLocation(code, step.location);
        buffer += step.dataValue + "";
        if (nextStep) buffer += getContentBetweenLocations(code, step.location, nextStep.location);
        else buffer += getContentAfterLocation(code, step.location);
    }
    return buffer; 
}

function isLocationWithinLocation(subLocation, location) {
    // (sub)location = [start line, start char, end line, start char]
    const isStartWithinLocation = (subLocation[0] > location[0]) || (subLocation[0] == location[0] && subLocation[1] >= location[1]);
    const isEndwithinLocation = (subLocation[2] < location[2]) || (subLocation[2] == location[2] && subLocation[3] <= location[3]);

    return isStartWithinLocation && isEndwithinLocation;
}

function getContentBeforeLocation(code,location) {
    return getContentWithinLocation(code, [1, 1, location[0], location[1]]);
}

function getContentBetweenLocations(code, location1, location2) {
    return getContentWithinLocation(code, [location1[2], location1[3] + 1, location2[0], location2[1]]);
}

function getContentWithinLocation(code, location) {
    const lines = code.split('\n');

    if (location[0] != location[2]) {
        return [
            lines[location[0] - 1].substring(location[1] - 1),
            ...lines.filter((_, i) => location[0] + 1 < i && i < location[2] - 1),
            lines[location[2] - 1].substring(0, location[3] - 1)
        ].join("\n");
    }
    return lines[location[0] - 1].substring(location[1] - 1, location[3] - 1);
}

function getContentAfterLocation(code, location) {
    const lines = code.split('\n');

    if (location[2] != lines.length) {
        return [
            lines[location[2] - 1].substring(location[3]),
            ...lines.filter((_, i) => i >= location[2])
        ].join("\n");
    }
    return lines[location[2] - 1].substring(location[3])
}

export default { stepForward, stepBackwards, getEvaluatedCode }