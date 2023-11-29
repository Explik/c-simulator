
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

// Based on https://stackoverflow.com/questions/14446511/most-efficient-method-to-groupby-on-an-array-of-objects
var groupBy = function(xs, key) {
    return xs.reduce(function(rv, x) {
      (rv[x[key]] = rv[x[key]] || []).push(x);
      return rv;
    }, {});
  };

/**
 * @param {SimulationStep} step
 * @returns {bool}
 */
export function isStatementStep(step) {
    return step.action == "stat";
} 

/**
 * @param {SimulationStep} step
 * @returns {bool}
 */
export function isExpressionStep(step) {
    return step.action == "eval";
}

/**
 * getFirstStep returns first breakable step in step sequence (nullable)
 * @param {function(SimulationStep)} isBreakStep
 * @param {SimulationStep[]} steps
 */
export function getFirstStep(isBreakStep, steps) {
    const index = steps.findIndex(isBreakStep);
    return (index !== -1) ? index : undefined;
}

/**
 * getNextStep returns next breakable step in step sequence (nullable)
 * @param {function(SimulationStep)} isBreakStep 
 * @param {SimulationStep[]} steps 
 * @param {number} currentIndex 
 */
export function getNextStep(isBreakStep, steps, currentIndex) {
    const offset = steps.slice(currentIndex + 1).findIndex(isBreakStep);
    return (offset !== -1) ? currentIndex + offset + 1 : undefined;
}

/**
 * getPreviousStep returns next breakable step in step sequence (nullable)
 * @param {function(SimulationStep)} isBreakStep 
 * @param {SimulationStep[]} steps 
 * @param {number} currentIndex 
 */
export function getPreviousStep(isBreakStep, steps, currentIndex) {
    const offset = steps.slice(0, currentIndex).findLastIndex(isBreakStep);
    return (offset !== -1) ? offset : undefined;
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

export function getHighlightedCode(code, steps) {
    const lastStatementIndex = steps.findLastIndex(s => s.action === "stat");
    if (lastStatementIndex === -1) return '';
    const lastStatement = steps[lastStatementIndex];
    const location = lastStatement.location;

    const evaluatedCode = getEvaluatedCode(code, steps);
    const lines = evaluatedCode.split('\n');
    
    const create = (n, v) => Array.from({length: n}, () => v).join(''); 
    const createLines = (n) => Array.from({length: n}, () => '');

    if (location[0] === location[2]) {
        const numberOfPrecedingLines = Math.max(0, location[0] - 1);
        const numberOfSucceedingLines = Math.max(0, lines.length - location[2]);
        const numberOfSquares = lines[location[2] - 1].length;

        return [
            ...createLines(numberOfPrecedingLines),
            create(numberOfSquares, '█'), 
            ...createLines(numberOfSucceedingLines),
        ].join("\n"); 
    }
    else throw new Error("Multi-line highlight is not supported");    
}

/**
 * Returns 
 * @param {SimulationStep[]} steps 
 */
export function getOutput(steps) {
    return steps
        .filter(s => s.action === "stdout")
        .map(s => s.value)
        .join("");
}

/**
 * Returns list of declared variables with current value
 * @param {SimulationStep[]} steps 
 * @returns { identifier: string,  dataType: string, dataValue: object }
 */
export function getVariables(steps) {
    const declarations = steps.filter(s => s.action == 'decl');
    const assignments = steps.filter(s => s.action == "assign");

    const groupedDeclarations = groupBy(declarations, 'identifier');
    const lastDeclarations = Object.keys(groupedDeclarations).map(k => {
        const value = groupedDeclarations[k];
        return value[value.length - 1];
    });
    
    return lastDeclarations.map(d => {
        const lastAssignment = [...assignments].reverse().find(s => s.identifier == d.identifier);
        const currentValue = lastAssignment ?? d;

        return {
            identifier: d.identifier,
            dataType: d.dataType,
            dataValue: currentValue.dataValue
        };
    });
}   

export default { isStatementStep, isExpressionStep, getFirstStep, getNextStep, getPreviousStep, getEvaluatedCode, getHighlightedCode, getOutput, getVariables }