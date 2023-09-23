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
            this.currentStep = this.allSteps[0];
        }
    }

    stepForward(mode) {
        this.currentStep = functions.stepForward(this.allSteps, this.currentStep, mode || "expression");
    }

    stepBackward(mode) {
        this.currentStep = functions.stepBackward(this.allSteps, this.currentStep, mode || "expression");
    }

    getCode() {
        return this.code;
    }

    getEvaluatedCode() {
        // gets code where changes are applied
        return this.code;
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