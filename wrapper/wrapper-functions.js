/**
 * @typedef SourceRange
 * @property {number} startIndex
 * @property {number} endIndex
 */

/**
 * @typedef SourceSegment
 * @property {number} startIndex
 * @property {number} endIndex
 * @property {string} value
 */

/**
 * @typedef SimulationStep
 * @property {string} action
 */

/**
 * @typedef SimulationVariable
 * @property {string} dataType
 * @property {string} dataValue
 * @property {SourceRange} scope
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
 * @param {SimulationStep} step
 * @returns {bool}
 */
export function isDeclarationStep(step) {
    return step.action == "decl";
}

/**
 * @param {SimulationStep} step
 * @returns {bool}
 */
export function isAssignmentStep(step) {
    return step.action == "decl";
}

/**
 * @param {SimulationStep} step
 * @returns {bool}
 */
export function isInvocationStep(step) {
    return step.action == "invocation";
}

/**
 * @param {SimulationStep} step
 * @returns {bool}
 */
export function isReturnStep(step) {
    return step.action == "return";
}

export function isSubrange(range, subrange) {
    return subrange[0] >= range.startIndex && subrange[1] <= range.endIndex;
}

export function isSubrangeStrict(range, subRange) {
    return subRange[0] > range.startIndex && subRange[1] < range.endIndex;
}

export function isWithin(range, index) {
    return index >= range.startIndex && index <= range.endIndex;
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
 * getCurrentStatementStep returns steps since and including last statement
 * @param {function(SimulationStep)} isStatement 
 * @param {SimulationStep[]} steps 
 * @returns {SimulationStep|undefined} 
 */
export function getCurrentStatementStep(steps) {
    const callstack = [[]];
    for (let step of steps) {
        if(isInvocationStep(step)) {
            callstack.push([]);
            callstack[callstack.length - 1].push(step);
        }
        else if (isReturnStep(step)) {
            callstack.pop();
        }
        else {
            callstack[callstack.length - 1].push(step);
        }
    }
    const frame = callstack[callstack.length - 1];
    const index = frame.findLastIndex(isStatementStep);
    return (index !== -1) ? frame[index] : undefined;    
}

/**
 * getCurrentStatementSteps returns steps since and including last statement
 * @param {function(SimulationStep)} isStatement 
 * @param {SimulationStep[]} steps 
 * @returns {SimulationStep[]} 
 */
export function getCurrentStatementSteps(steps) {
    const callstack = [[]];
    for (let step of steps) {
        if(isInvocationStep(step)) {
            callstack.push([]);
            callstack[callstack.length - 1].push(step);
        }
        else if (isReturnStep(step)) {
            callstack.pop();
        }
        else {
            callstack[callstack.length - 1].push(step);
        }
    }
    const frame = callstack[callstack.length - 1];
    const index = frame.findLastIndex(isStatementStep);
    return (index !== -1) ? frame.slice(index) : frame;    
}

/**
 * getEvaluatedSegment returns evaluated segment of code
 * @param {SimulationStep} expressionStep
 * @returns {SourceSegment}
 */
export function getEvaluatedSegment(expressionStep) {
    var value;
    var { dataType, dataValue, node } = expressionStep;
   
    switch(dataType) {
        case "int":
            value = `${dataValue}`;
            break;
        case "float":
            value = `${dataValue}f`;
            break;
        default:
            value = `${dataValue}`;
            break;
    }
    return { startIndex: node.range[0], endIndex: node.range[1], value };
}

/**
 * maskSegment returns 
 * @param {SourceSegment} step 
 * @returns {SourceSegment}
 */
export function maskSegment(step) {
    const { startIndex, endIndex, value} = step;
    const newValue = '█'.repeat(value.length);
    return { startIndex, endIndex, value: newValue };
}

/**
 * getNonOverlappingSegments returns an ordered list of non-overlapping segments 
 * @param {SourceSegment []} codeSegments 
 * 
 */
export function getNonOverlappingSegments(codeSegments) {
    const orderedCodeSegments = [...codeSegments];
    orderedCodeSegments.sort((s1, s2) => s2.startIndex - s1.startIndex);
    
    let buffer = [];
    for (let codeSegment of codeSegments) {
        // Remove any elements in buffer that 
        buffer = buffer.filter(c => !isSubrange(codeSegment, c));
        buffer.push(codeSegment);
    }
    return buffer;
}

/**
 * replaceSegments returns code with replaced code segments
 * @param {string} code 
 * @param {SourceSegment[]} codeSegments - non-overlapping code segments
 */
export function replaceSegments(code, codeSegments) {
    if (codeSegments.length === 0)
        return code;
    
    const buffer = [];
    for(let i = 0; i < codeSegments.length; i++) {
        const segment = codeSegments[i];
        const nextSegment = (i < codeSegments.length - 1) ? codeSegments[i + 1] : undefined;

        if (i == 0) 
            buffer.push(code.slice(0, segment.startIndex));
        
        buffer.push(segment.value);
        
        if (nextSegment)
            buffer.push(code.slice(segment.endIndex, nextSegment.startIndex));
        else
            buffer.push(code.slice(segment.endIndex));
    }
    return buffer.join("");
}

/**
 * getCurrentEvaluatedCode returns code with replaced evaluation steps
 * @param {string} code 
 * @param {SimulationStep[]} steps 
 * @returns {string}
 */
export function getCurrentEvaluatedCode(code, steps) {
    const statementSteps = getCurrentStatementSteps(steps);
    const evaluatedSegments = statementSteps.filter(isExpressionStep).map(getEvaluatedSegment);
    const nonOverlappingSegments = getNonOverlappingSegments(evaluatedSegments);
    return replaceSegments(code, nonOverlappingSegments);
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
        (s1, s2) => (s1.location[0] == s2.location[0]) ? s1.location[1] - s2.location[1] : s1.location[0] - s2.location[0]
    );

    return activeExpressionSteps.length ? getEvaluatedCodeInternal(code, activeExpressionSteps) : code;
}

function getLegacyLocation(code, range) {
    if (typeof code !== "string")
        throw Error("code is not of type string");
    if (!Array.isArray(range))
        throw Error("range is not of type Array");

    var startLines = code.slice(0, range[0]).split("\n");
    var endLines = code.slice(0, range[1]).split("\n");

    return [
        startLines.length,
        startLines[startLines.length - 1].length,
        endLines.length,
        endLines[endLines.length - 1].length
    ];
}

// Calculates evaluated code from a list of ordered non-overlapping steps
function getEvaluatedCodeInternal(code, activeSteps) {
    let buffer = "";

    for(let i = 0; i < activeSteps.length; i++) {
        const step = activeSteps[i];
        const stepLocation = step.location;
        const nextStep = (i < activeSteps.length - 1) ? activeSteps[i + 1] : undefined;

        if (i == 0) buffer += getContentBeforeLocation(code, stepLocation);
        buffer += step.dataValue + "";
        if (nextStep) buffer += getContentBetweenLocations(code, stepLocation, stepLocation);
        else buffer += getContentAfterLocation(code, stepLocation);
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
    steps.filter(s => s.node).forEach(s => s.location = getLegacyLocation(code, s.node.range));

    const lastStatement = getCurrentStatementStep(steps);
    if (lastStatement === undefined) return ''; 
    
    const location = lastStatement.location;
    const evaluatedCode = getEvaluatedCode(code, steps);
    const lines = evaluatedCode.split('\n');
    delete lastStatement.location;
    
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
export function getCurrentVariables(steps) {
    const declarations = steps.filter(s => s.action == 'decl' || s.action == "par");
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
            scope: d.scope,
            dataType: d.dataType,
            dataValue: currentValue.dataValue
        };
    });
}

export function getCurrentScopeVariables(steps) {
    const currentStatement = getCurrentStatementStep(steps);
    const currentVariables = getCurrentVariables(steps);

    return currentVariables.filter(v => isSubrange(v.scope, currentStatement.node.range));
}

export default { isStatementStep, isExpressionStep, getFirstStep, getNextStep, getPreviousStep, getEvaluatedCode, getHighlightedCode, getOutput, getVariables: getCurrentVariables }