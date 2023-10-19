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
            this.currentStep = functions.getFirstStep(this.allSteps, "expression");
        }
    }

    stepForward(mode) {
        let nextStep = functions.stepForward(this.allSteps, this.currentStep, mode || "expression");
        if (nextStep) this.currentStep = nextStep;
        return !!nextStep;
    }

    stepBackward(mode) {
        let previousStep = functions.stepBackward(this.allSteps, this.currentStep, mode || "expression");
        if (previousStep) this.currentStep = previousStep;
        return !!previousStep;
    }

    getCode() {
        return this.code;
    }

    getEvaluatedCode() {
        return functions.getEvaluatedCode(this.code, this.allSteps.slice(0, this.currentStep + 1));
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