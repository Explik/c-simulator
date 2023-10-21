
/**
 * @typedef SimulationStep
 * @property {string} action
 * 
 */

// Based on https://stackoverflow.com/questions/40929260/find-last-index-of-element-inside-array-by-certain-condition
function findLastIndex(array, predicate) {
    let l = array.length;
    while (l--) {
        if (predicate(array[l], l, array))
            return l;
    }
    return -1;
}

/**
 * 
 * @param {SimulationStep[]} steps 
 * @param {"expression"} mode
 * @returns {number}
 */
export function getFirstStep(steps, mode) {
    if (mode !== "expression")
        throw new error("Unsupported mode " + mode);

    const index = steps.findIndex(s => s.action === "eval");
    return (index !== -1) ? index : undefined;
}

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

    const offset = steps.slice(currentStep + 1).findIndex(s => s.action === "eval");
    return (offset !== -1) ? offset + currentStep + 1 : undefined;
}

/**
 * 
 * @param {SimulationStep[]} steps 
 * @param {number} currentStep 
 * @param {"expression"} mode
 * @returns {number}
 */
export function stepBackward(steps, currentStep, mode) {
    if (mode !== "expression")
        throw new error("Unsupported mode " + mode);

    const offset = steps.slice(0, currentStep).reverse().findIndex(s => s.action === "eval");
    return (offset !== -1) ? currentStep - offset - 1 : undefined;
}

/**
 * 
 * @param {string} code 
 * @param {SimulationStep[]} steps 
 */
export function getEvaluatedCode(code, steps) {
    // Filters out steps with encompased by other steps
    const lastStatementIndex = steps.findLastIndex(s => s.action === "stat");
    const lastStatementSteps = lastStatementIndex !== -1 ? steps.slice(lastStatementIndex) : steps;
    const expressionSteps = lastStatementSteps.filter(s => s.action === "eval");
    const activeExpressionSteps = expressionSteps.reduce(
        (steps, value) => [...steps.filter(s => !isLocationWithinLocation(s.location, value.location)), value],
        []
    );
    // Ordering steps according to start line and start charachter 
    activeExpressionSteps.sort(
        (s1, s2) => (s1.location[0] == s2.location[0]) ?  s1.location[1] - s2.location[1] : s1.location[0] - s2.location[0]
    );

    return activeExpressionSteps.length ? getEvaluatedCodeInternal(code, activeExpressionSteps) : code;
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
            ...lines.filter((_, i) => location[0] <= i && i < location[2] - 1),
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

/**
 * Returns list of declared variables with current value
 * @param {SimulationStep[]} steps 
 * @returns { identifier: string,  dataType: string, dataValue: object }
 */
export function getVariables(steps) {
    const declarations = steps.filter(s => s.action == 'decl');
    const assignments = steps.filter(s => s.action == "assign");

    return declarations.map(d => {
        const lastAssignment = assignments.reverse().find(s => s.identifier == d.identifier);
        const currentValue = lastAssignment ?? d;

        return {
            identifier: d.identifier,
            dataType: d.dataType,
            dataValue: currentValue.dataValue
        };
    });
}   

export default { stepForward, stepBackward, getFirstStep, getEvaluatedCode, getVariables }