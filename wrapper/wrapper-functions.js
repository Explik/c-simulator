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
 * @typedef SimulationEvalStep
 * @property {string} action
 * @property {string} dataType
 * @property {number} dataValue
 */

/**
 * @typedef SimulationDeclStep
 * @property {string} action
 * @property {string} identifier
 * @property {string} dataType
 * @property {number} dataValue
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

// == Utility functions ==
export function isSubrange(range, subrange) {
    return subrange.startIndex >= range.startIndex && subrange.endIndex <= range.endIndex;
}

export function isSubrangeStrict(range, subRange) {
    return subRange.startIndex > range.startIndex && subRange.endIndex < range.endIndex;
}

export function isWithin(range, index) {
    return index >= range.startIndex && index <= range.endIndex;
}

export function getCodePositions(range, code) {
    let currentLine = 1;
    let currentColumn = 1;
    let startLine, startColumn, endLine, endColumn;

    for (let i = 0; i < code.length; i++) {
        if (i === range.startIndex) {
            startLine = currentLine;
            startColumn = currentColumn;
        }
        if (i === range.endIndex) {
            // No need to continue once the end of the range is found
            endLine = currentLine;
            endColumn = currentColumn;
            break;
        }

        if (code[i] === '\n') {
            currentLine++;
            currentColumn = 1;
        } else {
            currentColumn++;
        }
    }
    return { startLine, startColumn, endLine, endColumn };
}

export function getCodeStartLine(range, code) {
    return getCodePositions(range, code).startLine;
}

// == Predicate functions ==
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
export function isParameterStep(step) {
    return step.action == "parameter";
}

/**
 * @param {SimulationStep} step
 * @returns {bool}
 */
export function isReturnStep(step) {
    return step.action == "return";
}

// == Stepping functions ==
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

// == Formatting function ==
/**
 * getFormattedName formats step as c identifier
 * @param {SimulationDeclStep} step 
 */
export function getFormattedName(step) {
    return step.identifier;
}

/**
 * getFormattedType formats step type as c type
 * @param {SimulationEvalStep} step 
 */
export function getFormattedType(step) {
    return step.dataType;
}

/**
 * getFormattedStringValue formats step value as equivalent c code 
 * @param {SimulationEvalStep} step 
 */
export function getFormattedStringValue(step) {
    var { dataType, dataValue } = step;
   
    switch(dataType) {
        case "int":
            return `${dataValue}`;
        case "float":
            return Number.isInteger(dataValue) ? dataValue.toFixed(2) + "f" : dataValue.toPrecision(5) + "f";
        case "double":
            return Number.isInteger(dataValue) ? dataValue.toFixed(2) : dataValue.toPrecision(5)
        default:
            return `${dataValue}`;
    }
}

// == Segment functions ==
/**
 * getEvaluatedCodeSegment returns evaluated segment of code
 * @param {SimulationEvalStep} evalStep
 * @returns {SourceSegment}
 */
export function getEvaluatedCodeSegment(evalStep) {
    var value = getFormattedStringValue(evalStep);

    return { 
        startIndex: evalStep.node.range.startIndex, 
        endIndex: evalStep.node.range.endIndex, 
        value 
    };
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
    for (let codeSegment of orderedCodeSegments) {
        // Remove any elements in buffer that 
        buffer = buffer.filter(c => !isSubrange(codeSegment, c));
        buffer.push(codeSegment);
    }
    buffer.sort((s1, s2) => s1.startIndex - s2.startIndex);
    return buffer;
}

/**
 * getTransformedCode returns code with replaced code segments
 * @param {string} code 
 * @param {SourceSegment[]} codeSegments - non-overlapping code segments
 */
export function getTransformedCode(code, codeSegments) {
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

export function getTransformedRange(originalRange, changes) {
    let { startIndex, endIndex } = originalRange;

    // Sort changes by starting index
    changes.sort((a, b) => a.startIndex - b.startIndex);

    for (const change of changes) {
        const changeLength = change.endIndex - change.startIndex;
        const insertLength = change.value.length;
        const lengthDifference = insertLength - changeLength;

        // Shift the entire range if the change is before it
        if (change.endIndex <= startIndex) {
            startIndex += lengthDifference;
            endIndex += lengthDifference;
        } 
        // Adjust the range if the change overlaps with it
        else if (change.startIndex < endIndex) {
            if (change.startIndex < startIndex) {
                startIndex += lengthDifference;
            }
            endIndex += lengthDifference;
        }
    }

    return { startIndex, endIndex };
}

// == State setup functions == 
export function attachCodePosition(code, nodes) {
    for (let node of nodes) {
        node.position = getCodePositions(node.range, code)
    }
}

export function attachStatementRef(steps, nodes) {
    const statementSteps = steps.filter(isStatementStep);
    const statementNodes = statementSteps.map(s => s.node).filter(n => n);
    const uniqueStatementNodes = Array.from(new Set(statementNodes.map(n => n.id))).map(id => statementNodes.find(n => n.id == id));
    uniqueStatementNodes.sort((n1, n2) => n1.range.startIndex - n2.range.startIndex); 

    if (uniqueStatementNodes.some(s => s.position === undefined))
        throw new Error("Statement nodes missing position property (use attachCodePosition)");

    for (let step of statementSteps) {
        const nodeStartLine = step.node.position.startLine;
        const statmentNodesOnLine = uniqueStatementNodes.filter(n => n.position.startLine == nodeStartLine);
        const statementNodeIndex = statmentNodesOnLine.findIndex(n => n.id == step.node.id) + 1;
        step.ref = `l${nodeStartLine}:${statementNodeIndex}`;
    }
}

// == State functions ==
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
 * 
 * @param {SimulationStep[]} steps 
 * @returns {SourceSegment[]}
 */
export function getCurrentStatementChanges(steps) {
    const statementSteps = getCurrentStatementSteps(steps);
    const evaluatedSegments = statementSteps.filter(isExpressionStep).map(getEvaluatedCodeSegment);
    return getNonOverlappingSegments(evaluatedSegments);
}


/**
 * @param {SimulationStep[]} steps 
 * @param {}
 */
export function getCurrentCallTree(steps) {
    let invocationId = -1; // Reset for every call of the function

    const root = { id: invocationId++, subcalls: [] };
    let stack = [root];

    for (const step of steps) {
        if (isInvocationStep(step)) {
            const currentInvoke = { 
                id: invocationId++, 
                invocation: step, 
                parameters: [], 
                return: [], 
                subcalls: [] 
            };
            stack[stack.length - 1].subcalls.push(currentInvoke);
            stack.push(currentInvoke);
        }
        else if (isParameterStep(step)) {
            stack[stack.length - 1].parameters.push(step);
        }
        else if (isReturnStep(step)) {
            stack[stack.length - 1].return.push(step);
            stack.pop();
        }
    }

    return root.subcalls.length === 1 ? root.subcalls[0] : undefined;
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
 * getCurrentEvaluatedCode returns code with replaced evaluation steps
 * @param {string} code 
 * @param {SimulationStep[]} steps 
 * @returns {string}
 */
export function getCurrentEvaluatedCode(code, steps) {
    const statementSteps = getCurrentStatementSteps(steps);
    const evaluatedSegments = statementSteps.filter(isExpressionStep).map(getEvaluatedCodeSegment);
    const nonOverlappingSegments = getNonOverlappingSegments(evaluatedSegments);
    return getTransformedCode(code, nonOverlappingSegments);
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