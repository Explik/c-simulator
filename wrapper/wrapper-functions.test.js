import assert from 'assert';
import { getEvaluatedCode, getFirstStep, getCurrentVariables, getNextStep, getPreviousStep, getCurrentStatementSteps, getEvaluatedCodeSegment, getNonOverlappingSegments, getTransformedCode, getFormattedStringValue, getTransformedRange, getCurrentCallTree } from './wrapper-functions.js';

describe("getFirstStep", function () {
  it('returns undefined when no step matches', function () {
    const steps = [
      { type: 'a' },
      { type: 'b' },
    ];
    const actual = getFirstStep(() => false, steps);

    assert.equal(actual, undefined);
  });
  it('returns first when first step matches', function () {
    const steps = [
      { type: 'a' },
      { type: 'b' },
    ];
    const actual = getFirstStep(s => s.type === 'a', steps);

    assert.equal(actual, 0);
  });
  it('returns first when first and second step matches', function () {
    const steps = [
      { type: 'a' },
      { type: 'a' },
    ];
    const actual = getFirstStep(s => s => s.type === 'a', steps);

    assert.equal(actual, 0);
  });
  it('returns second when second step matches', function () {
    const steps = [
      { type: 'a' },
      { type: 'b' },
    ];
    const actual = getFirstStep(s => s.type === 'b', steps);

    assert.equal(actual, 1);
  });
});

describe("getNextStep", function () {
  it('returns undefined when no steps matches', function () {
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
  it('returns undefined when no comming step matches', function () {
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
  it('returns next step when next step matches', function () {
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
  it('skips one step when next step does not match', function () {
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

describe("getPreviousStep", function () {
  it('returns undefined when no steps matches', function () {
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
  it('returns undefined when no comming step matches', function () {
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
  it('returns next step when next step matches', function () {
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
  it('skips one step when next step does not match', function () {
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

describe("getEvaluatedCode", function () {
  describe("getCurrentStatementSteps", function () {
    it('returns all steps when no step matches', function () {
      const steps = [
        { action: "eval" },
        { action: "eval" },
        { action: "eval" },
        { action: "eval" },
        { action: "eval" },
      ];
      const actual = getCurrentStatementSteps(steps);

      assert.deepEqual(actual, steps);
    });
    it('returns latter half of steps when one step matches', function () {
      const steps = [
        { action: "eval" },
        { action: "eval" },
        { action: "stat" }, // statement step
        { action: "eval" },
        { action: "eval" },
      ];
      const statementSteps = [
        { action: "stat" }, // statement step
        { action: "eval" },
        { action: "eval" },
      ];
      const actual = getCurrentStatementSteps(steps);

      assert.deepEqual(actual, statementSteps);
    });
    it('returns latter half of steps when one step matches', function () {
      const steps = [
        { action: "eval" },
        { action: "eval" },
        { action: "stat" }, // statement step
        { action: "stat" }, // statement step
        { action: "eval" },
      ];
      const statementSteps = [
        { action: "stat" }, // statement step 
        { action: "eval" },
      ];
      const actual = getCurrentStatementSteps(steps);

      assert.deepEqual(actual, statementSteps);
    });
    it('returns all steps after statement if no return', function () {
      const steps = [
        { action: "stat" },
        { action: "invocation" },
        { action: "stat" }, // statement step
        { action: "eval" },
        { action: "eval" },
      ];
      const statementSteps = [
        { action: "stat" }, // statement step 
        { action: "eval" },
        { action: "eval" },
      ];
      const actual = getCurrentStatementSteps(steps);

      assert.deepEqual(actual, statementSteps);
    });
    it('returns all steps prior to invoke with return', function () {
      const steps = [
        { action: "stat" }, // statement step 
        { action: "invocation" },
        { action: "stat" }, // statement step
        { action: "return" },
        { action: "eval" }, // statement step
        { action: "eval" }
      ];
      const statementSteps = [
        { action: "stat" }, // statement step 
        { action: "eval" },
        { action: "eval" },
      ];
      const actual = getCurrentStatementSteps(steps);

      assert.deepEqual(actual, statementSteps);
    });
  });
  describe("getFormattedStringValue", function () {
    it("returns 1234 for int resulting value", function () {
      const expressionStep = { startIndex: 2, endIndex: 3, dataType: "int", dataValue: 1234.0 };
      assert.deepEqual(getFormattedStringValue(expressionStep), "1234");
    });
    it("returns 2345.00f for whole-number float resulting value", function () {
      const expressionStep = { startIndex: 2, endIndex: 3, dataType: "float", dataValue: 2345.0 };
      assert.deepEqual(getFormattedStringValue(expressionStep), "2345.00f");
    });
  });
  describe("getNonOverlappingSegments", function () {
    it("returns last element if elements fully overlaps", function () {
      const codeSegments = [
        { startIndex: 2, endIndex: 3, value: "a" },
        { startIndex: 2, endIndex: 3, value: "1" }
      ];
      const expected = [codeSegments[1]];
      assert.deepEqual(getNonOverlappingSegments(codeSegments), expected);
    });

    it("returns last element if elements fully overlaps", function () {
      const codeSegments = [
        { startIndex: 2, endIndex: 3, value: "a" },
        { startIndex: 2, endIndex: 4, value: "1" }
      ];
      const expected = [codeSegments[1]];
      assert.deepEqual(getNonOverlappingSegments(codeSegments), expected);
    });

    it("returns both elements if elements do not overlap", function () {
      const codeSegments = [
        { startIndex: 1, endIndex: 2, value: "a" },
        { startIndex: 3, endIndex: 4, value: "b" }
      ];
      assert.deepEqual(getNonOverlappingSegments(codeSegments), codeSegments);
    });
  });
  describe("getTransformedCode", function () {
    it("does nothing on no segments", function () {
      const code = "int main() {}";
      assert.equal(getTransformedCode(code, []), code);
    });
    it("replaces one segment in beginning correct", function () {
      const code = "int main() {}";
      const segments = [{ startIndex: 0, endIndex: 3, value: "double" }];
      const expected = "double main() {}";
      assert.equal(getTransformedCode(code, segments), expected);
    });
    it("replaces one segment in middle correct", function () {
      const code = "int main() {}";
      const segments = [{ startIndex: 4, endIndex: 8, value: "main_2" }];
      const expected = "int main_2() {}";
      assert.equal(getTransformedCode(code, segments), expected);
    });
    it("replaces one segment at end correct", function () {
      const code = "int main() {}";
      const segments = [{ startIndex: 11, endIndex: 13, value: "{ exit(); }" }];
      const expected = "int main() { exit(); }";
      assert.equal(getTransformedCode(code, segments), expected);
    });
    it("replaces one segment in middle correct", function () {
      const code = "int main() {}";
      const segments = [
        { startIndex: 0, endIndex: 3, value: "double" },
        { startIndex: 11, endIndex: 13, value: "{ exit(); }" }
      ];
      const expected = "double main() { exit(); }";
      assert.equal(getTransformedCode(code, segments), expected);
    });
  });
  describe("getTransformedRange", function () {
    it('shifts range right with text insertion before range', () => {
      const originalRange = { startIndex: 10, endIndex: 15 };
      const changes = [{ startIndex: 5, endIndex: 5, value: "Hello" }];
      assert.deepEqual(getTransformedRange(originalRange, changes), { startIndex: 15, endIndex: 20 });
    });

    it('shifts range left with text deletion before range', () => {
      const originalRange = { startIndex: 10, endIndex: 15 };
      const changes = [{ startIndex: 2, endIndex: 7, value: "" }];
      assert.deepEqual(getTransformedRange(originalRange, changes), { startIndex: 5, endIndex: 10 });
    });

    it('expands range with text insertion within range', () => {
      const originalRange = { startIndex: 5, endIndex: 10 };
      const changes = [{ startIndex: 7, endIndex: 7, value: "World" }];
      assert.deepEqual(getTransformedRange(originalRange, changes), { startIndex: 5, endIndex: 15 });
    });

    it('contracts range with text deletion within range', () => {
      const originalRange = { startIndex: 5, endIndex: 10 };
      const changes = [{ startIndex: 7, endIndex: 9, value: "" }];
      assert.deepEqual(getTransformedRange(originalRange, changes), { startIndex: 5, endIndex: 8 });
    });
  });
});

describe('getVariables', function () {
  it('returns variable as declared when not reassigned', function () {
    const steps = [{
      action: 'decl',
      identifier: 'i',
      dataType: 'int',
      dataValue: 7
    }];
    const actual = getCurrentVariables(steps);
    const expected = [{
      identifier: 'i',
      dataType: 'int',
      dataValue: 7,
      scope: undefined
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
    const actual = getCurrentVariables(steps);
    const expected = [
      {
        identifier: 'i',
        dataType: 'int',
        dataValue: 7,
        scope: undefined
      },
      {
        identifier: 'j',
        dataType: 'int',
        dataValue: 8,
        scope: undefined
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
    const actual = getCurrentVariables(steps);
    const expected = [{
      identifier: 'i',
      dataType: 'int',
      dataValue: 8,
      scope: undefined
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
    const actual = getCurrentVariables(steps);
    const expected = [{
      identifier: 'i',
      dataType: 'int',
      dataValue: 9,
      scope: undefined
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
    const actual = getCurrentVariables(steps);
    const expected = [{
      identifier: 'i',
      dataType: 'double',
      dataValue: 8,
      scope: undefined
    }];

    assert.deepEqual(actual, expected);
  });
});

describe("getCurrentCallTree", function () {
  it('should handle a single invocation with no parameters or returns', function () {
    const steps = [{ action: "invocation" }, { action: "return" }];
    const expected = {
      id: 0,
      invocation: { action: "invocation" },
      parameters: [],
      return: [{ action: "return" }],
      subcalls: []
    };
    assert.deepEqual(getCurrentCallTree(steps), expected);
  });

  it('should handle invocations with parameters', function () {
    const steps = [
      { action: "invocation" },
      { action: "parameter" },
      { action: "parameter" },
      { action: "return" }
    ];
    const expected = {
      id: 0,
      invocation: { action: "invocation" },
      parameters: [{ action: "parameter" }, { action: "parameter" }],
      return: [{ action: "return" }],
      subcalls: []
    };
    assert.deepEqual(getCurrentCallTree(steps), expected);
  });

  it('should handle nested invocations', function () {
    const steps = [
      { action: "invocation" },
      { action: "parameter" },
      { action: "invocation" },
      { action: "return" },
      { action: "return" }
    ];
    const expected = {
      id: 0,
      invocation: { action: "invocation" },
      parameters: [{ action: "parameter" }],
      return: [{ action: "return" }],
      subcalls: [
        {
          id: 1,
          invocation: { action: "invocation" },
          parameters: [],
          return: [{ action: "return" }],
          subcalls: []
        }
      ]
    };
    assert.deepEqual(getCurrentCallTree(steps), expected);
  });

  it('should return undefined for an empty input', function () {
    const steps = [];
    assert.deepEqual(getCurrentCallTree(steps), undefined);
  });
});