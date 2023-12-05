/**
 * @typedef Module
 * @property {function} _main
 * @property {string} simulatorCode
 * @property {SimulationStep[]} simulatorSteps
 */
import {isExpressionStep, isStatementStep, getFirstStep, getPreviousStep, getNextStep, getHighlightedCode, getCurrentScopeVariables, getOutput, getCurrentEvaluatedCode, getCurrentStatementStep } from './wrapper-functions.js'

class Simulation {
    isBreakStep = (s) => isExpressionStep(s) || isStatementStep(s);

    /**
     * DO NOT USE DIRECTLY
     * @param {Module} module
     */
    constructor(module) {
        this.code = undefined;
        this.allSteps = [];
        this.currentStep = undefined;
        this.isRunning = false; 
        this.module = module;
    }

    run() {
        if (!this.isRunning) {
            // Run simulation
            const module = this.module;
            this.isRunning = true;
            module._main();
            
            // Link data 
            module.simulatorSteps.forEach(s => s.node = module.simulatorNodes.find(n => n.id == s.nodeId));
            module.simulatorSteps.filter(s => s.node).forEach(s => s.snippet = module.simulatorCode.slice(s.node.range[0], s.node.range[1]));
            
            // Expose data 
            this.code = module.simulatorCode;
            this.allSteps = module.simulatorSteps;
            this.currentStep = getFirstStep(this.isBreakStep, this.allSteps);
        }
    }

    stepForward() {
        let nextStep = getNextStep(this.isBreakStep, this.allSteps, this.currentStep);
        if (nextStep !== undefined) this.currentStep = nextStep;
        return nextStep !== undefined;
    }

    stepBackward() {
        let previousStep = getPreviousStep(this.isBreakStep, this.allSteps, this.currentStep);
        if (previousStep !== undefined) this.currentStep = previousStep;
        return previousStep !== undefined;
    }

    getCode() {
        return this.code;
    }

    getEvaluatedCode() {
        return getCurrentEvaluatedCode(this.code, this.allSteps.slice(0, this.currentStep + 1));
    }

    getHighlightedCode() {
        return getHighlightedCode(this.code, this.allSteps.slice(0, this.currentStep + 1)); 
    }

    getOutput() {
        const prefix = "> program.exe\n";
        return prefix + getOutput(this.allSteps.slice(0, this.currentStep + 1))
    }

    getVariables() {
        return getCurrentScopeVariables(this.allSteps.slice(0, this.currentStep + 1))
    }

    getCurrentStatement() {
        const currentStatementStep = getCurrentStatementStep(this.allSteps.slice(0, this.currentStep + 1))
        const currentStatement = this.module.simulatorNodes.find(s => s.id == currentStatementStep.statementId);
        return currentStatement.ref;
    }

    /**
     * 
     * @param {Module} module 
     */
    static create(module) {
        return new Simulation(module);
    }
}

export default Simulation;