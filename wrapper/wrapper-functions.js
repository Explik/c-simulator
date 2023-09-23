
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
function stepForward(steps, currentStep, mode) {
    if (mode !== "expression")
        throw new error("Unsupported mode " + mode);

    return currentStep < steps.length - 1 ? currentStep + 1 : currentStep;
}

/**
 * 
 * @param {SimulationStep[]} steps 
 * @param {number} currentStep 
 * @param {"expression"} mode
 * @returns {number}
 */
function stepBackwards(steps, currentStep, mode) {
    if (mode !== "expression")
        throw new error("Unsupported mode " + mode);

    return currentStep > 0 ? currentStep - 1 : currentStep;
}

/**
 * 
 * @param {string} code 
 * @param {SimulationStep[]} steps 
 */
function getEvaluatedCode(code, steps) {

}

/**
 * @param {SimulationStep[]} steps
 */
function applyCodeChange(steps) {
    
}


export default { stepForward, stepBackwards, getEvaluatedCode }