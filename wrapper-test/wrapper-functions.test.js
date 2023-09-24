import assert from 'assert';
import { stepForward, stepBackwards, getEvaluatedCode } from '../wrapper/wrapper-functions.js';

describe('getEvaluatedCode', function () {
  it('replaces expression at beginning', function () {
    const code = "5 * 7 + 6;";
    const steps = [{
      type: 'expression',
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
      type: 'expression',
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
      type: 'expression',
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
      type: 'expression',
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
        type: 'expression',
        dataType: "int",
        dataValue: 35,
        location: [1, 1, 1, 5]
      }, {
        type: 'expression',
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
        type: 'expression',
        dataType: "int",
        dataValue: 9,
        location: [2, 11, 2, 15]
      }, {
        type: 'expression',
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
        type: 'expression',
        dataType: "int",
        dataValue: 35,
        location: [2, 10, 2, 14]
      }, {
        type: 'expression',
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
        type: 'expression',
        dataType: "int",
        dataValue: 35,
        location: [1, 1, 1, 5]
      },
      {
        type: 'expression',
        dataType: "int",
        dataValue: 41,
        location: [1, 1, 1, 9]
      }
    ];

    const actual = getEvaluatedCode(code, steps);
    const expected = "41;";
    assert.equal(actual, expected);
  });
});