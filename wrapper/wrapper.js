/**
 * @typedef Module
 * @property {function} _main
 * @property {string} simulatorCode
 * @property {SimulationStep[]} simulatorSteps
 */
import functions from './wrapper-functions.js'

class Simulation {
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
            this.currentStep = 0;
        }
    }

    stepForward(mode) {
        let nextStep = functions.stepForward(this.allSteps, this.currentStep, mode || "expression");
        if (nextStep !== undefined) this.currentStep = nextStep;
        return !!nextStep;
    }

    stepBackward(mode) {
        let previousStep = functions.stepBackward(this.allSteps, this.currentStep, mode || "expression");
        this.currentStep = previousStep ?? 0;
        return !!previousStep;
    }

    getCode() {
        return this.code;
    }

    getEvaluatedCode() {
        return functions.getEvaluatedCode(this.code, this.allSteps.slice(0, this.currentStep + 1));
    }

    getVariables() {
        return functions.getVariables(this.allSteps.slice(0, this.currentStep + 1))
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