import assert from 'assert';
import { getEvaluatedCode, getFirstStep, getVariables, getHighlightedCode, getNextStep, getPreviousStep, getCurrentStatementSteps, getEvaluatedSegment, getNonOverlappingSegments, replaceSegments } from './wrapper-functions.js';

describe("getFirstStep", function() {
  it ('returns undefined when no step matches', function() {
    const steps = [
      { type: 'a' },
      { type: 'b' },
    ];
    const actual = getFirstStep(() => false, steps);

    assert.equal(actual, undefined);
  });
  it ('returns first when first step matches', function() {
    const steps = [
      { type: 'a' },
      { type: 'b' },
    ];
    const actual = getFirstStep(s => s.type === 'a', steps);

    assert.equal(actual, 0);
  });
  it ('returns first when first and second step matches', function() {
    const steps = [
      { type: 'a' }, 
      { type: 'a' },
    ];
    const actual = getFirstStep(s => s => s.type === 'a', steps);

    assert.equal(actual, 0);
  });
  it ('returns second when second step matches', function() {
    const steps = [
      { type: 'a' },
      { type: 'b' },
    ];
    const actual = getFirstStep(s => s.type === 'b', steps);

    assert.equal(actual, 1);
  });
});

describe("getNextStep", function() {
  it ('returns undefined when no steps matches', function() {
    const steps = [
      { type: 'a' }, // current step
      { type: 'b' },
      { type: 'c' },
      { type: 'd' },
      { type: 'e' },
      { type: 'f' }
    ];
    const actual = getNextStep(() => false, steps, 0);

    assert.equal(actual, undefined);
  });
  it ('returns undefined when no comming step matches', function() {
    const steps = [
      { type: 'a' }, 
      { type: 'b' }, // current step
      { type: 'c' },
      { type: 'd' },
      { type: 'e' },
      { type: 'f' }
    ];
    const actual = getNextStep(s => s.type == 'b', steps, 1);

    assert.equal(actual, undefined);
  });
  it ('returns next step when next step matches', function() {
    const steps = [
      { type: 'a' }, 
      { type: 'b' },
      { type: 'c' }, // current step
      { type: 'd' }, // next step
      { type: 'e' },
      { type: 'f' }
    ];
    const actual = getNextStep(s => s.type == 'd', steps, 2);

    assert.equal(actual, 3);
  });
  it ('skips one step when next step does not match', function() {
    const steps = [
      { type: 'a' }, 
      { type: 'b' },
      { type: 'c' }, 
      { type: 'd' }, // current step
      { type: 'e' },
      { type: 'f' }  // next step
    ];
    const actual = getNextStep(s => s.type == 'f', steps, 3);

    assert.equal(actual, 5);
  });
});

describe("getPreviousStep", function() {
  it ('returns undefined when no steps matches', function() {
    const steps = [
      { type: 'a' },
      { type: 'b' },
      { type: 'c' },
      { type: 'd' },
      { type: 'e' },
      { type: 'f' } // current step
    ];
    const actual = getPreviousStep(() => false, steps, 5);

    assert.equal(actual, undefined);
  });
  it ('returns undefined when no comming step matches', function() {
    const steps = [
      { type: 'a' },
      { type: 'b' }, 
      { type: 'c' },
      { type: 'd' },
      { type: 'e' }, // current step 
      { type: 'f' }
    ];
    const actual = getPreviousStep(s => s.type == 'e', steps, 4);

    assert.equal(actual, undefined);
  });
  it ('returns next step when next step matches', function() {
    const steps = [
      { type: 'a' }, 
      { type: 'b' },
      { type: 'c' }, // previous step
      { type: 'd' }, // current step
      { type: 'e' },
      { type: 'f' }
    ];
    const actual = getPreviousStep(s => s.type == 'c', steps, 3);

    assert.equal(actual, 2);
  });
  it ('skips one step when next step does not match', function() {
    const steps = [
      { type: 'a' }, 
      { type: 'b' }, // previous step
      { type: 'c' }, 
      { type: 'd' }, // current step
      { type: 'e' },
      { type: 'f' }
    ];
    const actual = getPreviousStep(s => s.type == 'b', steps, 3);

    assert.equal(actual, 1);
  });
});

describe("getEvaluatedCode", function() {
  describe("getCurrentStatementSteps", function() {
    it ('returns all steps when no step matches', function() {
      const steps = [
        { type: 'a' },
        { type: 'b' },
        { type: 'c' },
        { type: 'd' },
        { type: 'e' },
      ];
      const actual = getCurrentStatementSteps(() => false, steps);
  
      assert.deepEqual(actual, steps);
    });
    it ('returns latter half of steps when one step matches', function() {
      const steps = [
        { type: 'a' },
        { type: 'b' },
        { type: 'c' }, // statement step
        { type: 'd' },
        { type: 'e' },
      ];
      const statementSteps = [
        { type: 'c' }, // statement step
        { type: 'd' },
        { type: 'e' },
      ];
      const actual = getCurrentStatementSteps(s => s.type === "c", steps);
  
      assert.deepEqual(actual, statementSteps);
    });
    it ('returns latter half of steps when one step matches', function() {
      const steps = [
        { type: 'a' },
        { type: 'b' },
        { type: 'c' }, // statement step
        { type: 'd' }, // statement step
        { type: 'e' },
      ];
      const statementSteps = [
        { type: 'd' }, // statement step 
        { type: 'e' },
      ];
      const actual = getCurrentStatementSteps(s => s.type === "c" || s.type === "d", steps);
  
      assert.deepEqual(actual, statementSteps);
    });
  });
  describe("getEvaluatedSegment", function() {
    it ("returns 1234 for int resulting value", function() {
      const expressionStep = { startIndex: 2, endIndex: 3, dataType: "int", dataValue: 1234.0};
      const expected = { startIndex: 2, endIndex: 3, value: "1234" };
      assert.deepEqual(getEvaluatedSegment(expressionStep), expected);
    });
    it ("returns 2345f for float resulting value", function() {
      const expressionStep = { startIndex: 2, endIndex: 3, dataType: "float", dataValue: 2345.0};
      const expected = { startIndex: 2, endIndex: 3, value: "2345f" };
      assert.deepEqual(getEvaluatedSegment(expressionStep), expected);
    });
  });
  describe("getNonOverlappingSegments", function() {
    it ("returns last element if elements fully overlaps", function() {
      const codeSegments = [
        { startIndex: 2, endIndex: 3, value: "a" },
        { startIndex: 2, endIndex: 3, value: "1" }
      ];
      const expected = [ codeSegments[1] ];
      assert.deepEqual(getNonOverlappingSegments(codeSegments), expected);
    });

    it ("returns last element if elements fully overlaps", function() {
      const codeSegments = [
        { startIndex: 2, endIndex: 3, value: "a" },
        { startIndex: 2, endIndex: 4, value: "1" }
      ];
      const expected = [ codeSegments[1] ];
      assert.deepEqual(getNonOverlappingSegments(codeSegments), expected);
    });

    it ("returns both elements if elements do not overlap", function() {
      const codeSegments = [
        { startIndex: 1, endIndex: 2, value: "a" },
        { startIndex: 3, endIndex: 4, value: "b" }
      ];
      assert.deepEqual(getNonOverlappingSegments(codeSegments), codeSegments);
    });
  });
  describe("replaceSegments", function() {
    it("replaces one segment in beginning correct", function() {
      const code = "int main() {}";
      const segments = [ { startIndex: 0, endIndex: 3, value: "double" } ];
      const expected = "double main() {}";
      assert.equal(replaceSegments(code, segments), expected);
    });
    it("replaces one segment in middle correct", function() {
      const code = "int main() {}";
      const segments = [ { startIndex: 4, endIndex: 8, value: "main_2" } ];
      const expected = "int main_2() {}";
      assert.equal(replaceSegments(code, segments), expected);
    });
    it("replaces one segment at end correct", function() {
      const code = "int main() {}";
      const segments = [ { startIndex: 11, endIndex: 13, value: "{ exit(); }" } ];
      const expected = "int main() { exit(); }";
      assert.equal(replaceSegments(code, segments), expected);
    });
    it("replaces one segment in middle correct", function() {
      const code = "int main() {}";
      const segments = [ 
        { startIndex: 0, endIndex: 3, value: "double" },
        { startIndex: 11, endIndex: 13, value: "{ exit(); }" } 
      ];
      const expected = "double main() { exit(); }";
      assert.equal(replaceSegments(code, segments), expected);
    });
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
  it('returns last declaration', function () {
    const steps = [
      {
        action: 'decl',
        identifier: 'i',
        dataType: 'int',
        dataValue: 7
      },
      {
        action: 'decl',
        identifier: 'i',
        dataType: 'double',
        dataValue: 8
      }
    ];
    const actual = getVariables(steps);
    const expected = [{
      identifier: 'i',
      dataType: 'double',
      dataValue: 8
    }];

    assert.deepEqual(actual, expected);
  });
});