/**
 * @typedef Module
 * @property {function} _main
 * @property {string} simulatorCode
 * @property {SimulationStep[]} simulatorSteps
 */
import {isExpressionStep, isStatementStep, getFirstStep, getPreviousStep, getNextStep, getCurrentScopeVariables, getOutput, getCurrentEvaluatedCode, getCurrentStatementChanges, getCurrentStatementStep, attachCodePosition, attachStatementRef, getCurrentCallTree} from './wrapper-functions.js'


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
            module.simulatorNodes.forEach(n => {
                n.parent = module.simulatorNodes.find(n2 => n2.id == n.parentId);
                if (n.parent) {
                    n.parent.children = n.parent?.children ?? [];
                    n.parent.children.push(n);
                }
            });

            module.simulatorSteps.filter(s => s.node).forEach(s => s.snippet = module.simulatorCode.slice(s.node.range.startIndex, s.node.range.endIndex));
            
            attachCodePosition(module.simulatorCode, module.simulatorNodes);
            attachStatementRef(module.simulatorSteps, module.simulatorNodes);

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

    getOutput() {
        const prefix = "> program.exe\n";
        return prefix + getOutput(this.allSteps.slice(0, this.currentStep + 1))
    }

    getCurrentScopeVariables() {
        return getCurrentScopeVariables(this.allSteps.slice(0, this.currentStep + 1))
    }

    getCurrentCallTree() {
        return getCurrentCallTree(this.allSteps.slice(0, this.currentStep + 1));
    }

    getCurrentStatementChanges() {
        return getCurrentStatementChanges(this.allSteps.slice(0, this.currentStep + 1));
    }

    getCurrentStatementRange() {
        return getCurrentStatementStep(this.allSteps.slice(0, this.currentStep + 1)).node.range;
    }

    getCurrentStatementRef() {
        return getCurrentStatementStep(this.allSteps.slice(0, this.currentStep + 1)).ref;
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