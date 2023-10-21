import assert from 'assert';
import { stepForward, stepBackward, getEvaluatedCode, getFirstStep, getVariables, getHighlightedCode } from './wrapper-functions.js';

describe("getFirstStep", function() {
  it ('returns undefined when all steps are non-expression', function() {
    const steps = [
      { action: 'decl' },
      { action: 'decl' },
    ];
    const actual = getFirstStep(steps, "expression");

    assert.equal(actual, undefined);
  });
  it ('returns zero when first step is expression', function() {
    const steps = [
      { action: 'eval' },
      { action: 'eval' },
    ];
    const actual = getFirstStep(steps, "expression");

    assert.equal(actual, 0);
  });
  it ('returns one when second step is expression', function() {
    const steps = [
      { action: 'decl' },
      { action: 'eval' },
    ];
    const actual = getFirstStep(steps, "expression");

    assert.equal(actual, 1);
  });
});

describe('stepForward', function () {
  it ('returns undefined when all next steps are non-expression', function() {
    const steps = [
      { action: 'eval' },
      { action: 'eval' }, // currentStep
      { action: 'decl' },
      { action: 'decl' },
      { action: 'decl' }
    ];
    const actual = stepForward(steps, 1, 'expression');

    assert.equal(actual, undefined);
  });
  it('skips none when the next step is expression', function () {
    const steps = [
      { action: 'eval' },
      { action: 'eval' }, // currentStep
      { action: 'eval' },
      { action: 'eval' },
      { action: 'eval' }
    ];
    const actual = stepForward(steps, 1, 'expression');

    assert.equal(actual, 2);
  });
  it('skips one when the next step is declaration', function () {
    const steps = [
      { action: 'eval' },
      { action: 'eval' }, // currentStep
      { action: 'decl' },
      { action: 'eval' },
      { action: 'eval' }
    ];
    const actual = stepForward(steps, 1, 'expression');

    assert.equal(actual, 3);
  });
  it('skips two when the two next steps are declarations ', function () {
    const steps = [
      { action: 'eval' },
      { action: 'eval' }, // currentStep
      { action: 'decl' },
      { action: 'decl' },
      { action: 'eval' }
    ];
    const actual = stepForward(steps, 1, 'expression');

    assert.equal(actual, 4);
  });
});

describe('stepBackward', function() {
  it ('returns undefined when all previous steps are non-expression', function() {
    const steps = [
      { action: 'decl' },
      { action: 'decl' },
      { action: 'decl' },
      { action: 'eval' }, // currentStep
      { action: 'eval' }
    ];
    const actual = stepBackward(steps, 3, 'expression');

    assert.equal(actual, undefined);
  });
  it('skips none when the next step is expression', function () {
    const steps = [
      { action: 'eval' },
      { action: 'eval' },
      { action: 'eval' },
      { action: 'eval' }, // currentStep
      { action: 'eval' }
    ];
    const actual = stepBackward(steps, 3, 'expression');

    assert.equal(actual, 2);
  });
  it('skips one when the previous step is non-expression', function () {
    const steps = [
      { action: 'eval' },
      { action: 'eval' },
      { action: 'decl' },
      { action: 'eval' }, // currentStep
      { action: 'eval' }
    ];
    const actual = stepBackward(steps, 3, 'expression');

    assert.equal(actual, 1);
  });
  it('skips none when the two previous step is non-expression', function () {
    const steps = [
      { action: 'eval' },
      { action: 'decl' },
      { action: 'decl' },
      { action: 'eval' }, // currentStep
      { action: 'eval' }
    ];
    const actual = stepBackward(steps, 3, 'expression');

    assert.equal(actual, 0);
  });
});

describe('getEvaluatedCode', function () {
  it('replaces expression at beginning', function () {
    const code = "5 * 7 + 6;";
    const steps = [{
      action: 'eval',
      dataType: "int",
      dataValue: 35,
      location: [1, 1, 1, 5]
    }];

    const actual = getEvaluatedCode(code, steps);
    const expected = "35 + 6;";
    assert.equal(actual, expected);
  });
  it('replaces expression in middle', function () {
    const code = "f(5 * 7);";
    const steps = [{
      action: 'eval',
      dataType: "int",
      dataValue: 35,
      location: [1, 3, 1, 7]
    }];

    const actual = getEvaluatedCode(code, steps);
    const expected = "f(35);";
    assert.equal(actual, expected);
  });
  it('replaces expression in middle (multi-line)', function () {
    const code = "int main() {\n  return 5 * 7 + 6;\n}";
    const steps = [{
      action: 'eval',
      dataType: "int",
      dataValue: 35,
      location: [2, 10, 2, 14]
    }];

    const actual = getEvaluatedCode(code, steps);
    const expected = "int main() {\n  return 35 + 6;\n}";
    assert.equal(actual, expected);
  });
  it('replaces expression at end', function () {
    const code = "6 + 5 * 7;";
    const steps = [{
      action: 'eval',
      dataType: "int",
      dataValue: 35,
      location: [1, 5, 1, 9]
    }];

    const actual = getEvaluatedCode(code, steps);
    const expected = "6 + 35;";
    assert.equal(actual, expected);
  });
  it('replaces non-overlapping expressions', function () {
    const code = "5 * 7 + 6 * 3;";
    const steps = [
      {
        action: 'eval',
        dataType: "int",
        dataValue: 35,
        location: [1, 1, 1, 5]
      }, {
        action: 'eval',
        dataType: 'int',
        dataValue: 18,
        location: [1, 9, 1, 13]
      }
    ];

    const actual = getEvaluatedCode(code, steps);
    const expected = "35 + 18;";
    assert.equal(actual, expected);
  });
  it('replaces non-overlapping expressions on different lines', function () {
    const code = "int main() {\n  int i = 3 * 3;\n  return i;\n}";
    const steps = [
      {
        action: 'eval',
        dataType: "int",
        dataValue: 9,
        location: [2, 11, 2, 15]
      }, {
        action: 'eval',
        dataType: 'int',
        dataValue: 9,
        location: [3, 10, 3, 10]
      }
    ];

    const actual = getEvaluatedCode(code, steps);
    const expected = "int main() {\n  int i = 9;\n  return 9;\n}";
    assert.equal(actual, expected);
  });
  it('replaces non-overlapping expressions on same line', function () {
    const code = "int main() {\n  return 5 * 7 + 6 * 3;\n}";
    const steps = [
      {
        action: 'eval',
        dataType: "int",
        dataValue: 35,
        location: [2, 10, 2, 14]
      }, {
        action: 'eval',
        dataType: 'int',
        dataValue: 18,
        location: [2, 18, 2, 22]
      }
    ];

    const actual = getEvaluatedCode(code, steps);
    const expected = "int main() {\n  return 35 + 18;\n}";
    assert.equal(actual, expected);
  });
  it('replaces overlapped expressions', function () {
    const code = "5 * 7 + 6;";
    const steps = [
      {
        action: 'eval',
        dataType: "int",
        dataValue: 35,
        location: [1, 1, 1, 5]
      },
      {
        action: 'eval',
        dataType: "int",
        dataValue: 41,
        location: [1, 1, 1, 9]
      }
    ];

    const actual = getEvaluatedCode(code, steps);
    const expected = "41;";
    assert.equal(actual, expected);
  });
  it('replaces expression after statement', function() {
    const code = "5 * 7; 6 * 3;";
    const steps = [
      {
        action: 'eval',
        dataType: "int",
        dataValue: 35,
        location: [1, 1, 1, 5]
      },
      { 
        action: 'stat' 
      },
      {
        action: 'eval',
        dataType: 'int',
        dataValue: 18,
        location: [1, 8, 1, 12]
      }
    ];

    const actual = getEvaluatedCode(code, steps);
    const expected = "5 * 7; 18;";
    assert.equal(actual, expected);
  });
});

describe('getHighlightedCode', function () {
  it('highlights expression in middle (multi-line)', function () {
    const code = "int main() {\n  return 5 * 7 + 6;\n}";
    const steps = [{
      action: 'stat',
      location: [2, 3, 2, 14]
    }];

    const actual = getHighlightedCode(code, steps);
    const expected = "\n███████████████████\n";
    assert.equal(actual, expected);
  });
});

describe('getVariables', function() {
  it ('returns variable as declared when not reassigned', function() {
    const steps = [{
      action: 'decl',
      identifier: 'i',
      dataType: 'int',
      dataValue: 7
    }];
    const actual = getVariables(steps);
    const expected = [{
      identifier: 'i',
      dataType: 'int',
      dataValue: 7
    }]
    assert.deepEqual(actual, expected);
  });
  it('returns variables as declared when not reassigned', function () {
    const steps = [
      {
        action: 'decl',
        identifier: 'i',
        dataType: 'int',
        dataValue: 7
      },
      {
        action: 'decl',
        identifier: 'j',
        dataType: 'int',
        dataValue: 8
      }
    ];
    const actual = getVariables(steps);
    const expected = [
      {
        identifier: 'i',
        dataType: 'int',
        dataValue: 7
      },
      {
        identifier: 'j',
        dataType: 'int',
        dataValue: 8
      }
    ];

    assert.deepEqual(actual, expected);
  });
  it('returns variable as assigned when reassigned once', function () {
    const steps = [
      {
        action: 'decl',
        identifier: 'i',
        dataType: 'int',
        dataValue: 7
      },
      {
        action: 'assign',
        identifier: 'i',
        dataType: 'int',
        dataValue: 8
      }
    ];
    const actual = getVariables(steps);
    const expected = [{
      identifier: 'i',
      dataType: 'int',
      dataValue: 8
    }];

    assert.deepEqual(actual, expected);
  });
  it('returns variable as assigned when reassigned multiple times', function () {
    const steps = [
      {
        action: 'decl',
        identifier: 'i',
        dataType: 'int',
        dataValue: 7
      },
      {
        action: 'assign',
        identifier: 'i',
        dataType: 'int',
        dataValue: 8
      },
      {
        action: 'assign',
        identifier: 'i',
        dataType: 'int',
        dataValue: 9
      }
    ];
    const actual = getVariables(steps);
    const expected = [{
      identifier: 'i',
      dataType: 'int',
      dataValue: 9
    }];

    assert.deepEqual(actual, expected);
  });
});