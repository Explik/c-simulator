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
            this.isRunning = true;
            this.module._main();
            
            this.code = this.module.simulatorCode;
            this.allSteps = this.module.simulatorSteps;
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
        this.currentStep = previousStep ?? 0;
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
        const currentStatementStep = getCurrentStatementStep(isStatementStep, this.allSteps.slice(0, this.currentStep + 1))
        const currentStatement = this.module.simulatorStatements.find(s => s.id == currentStatementStep.statementId);
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