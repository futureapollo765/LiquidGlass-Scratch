/** Independent interpretation of the saved 480 × 360 calibration-grid source. */
const assert = require('node:assert/strict');
const width = 480, height = 360;

function gridPixel(stored, rows, logicalIndex, compact) {
    assert.ok(Number.isInteger(logicalIndex) && logicalIndex >= 1 && logicalIndex <= width * height);
    if (stored.length === width * height) return stored[logicalIndex - 1];
    if (compact) stored = compact();
    assert.equal(stored.length % width, 0, 'Compressed RGB rows must be complete');
    const map = rows();
    assert.equal(map.length, height, 'Grid row map must cover the logical stage');
    const row = Number(map[Math.floor((logicalIndex - 1) / width)]);
    assert.ok(Number.isInteger(row) && row >= 1 && row <= stored.length / width, 'Invalid compact row ordinal');
    return stored[(row - 1) * width + ((logicalIndex - 1) % width)];
}

function logicalGrid(stored, rows, compact) {
    if (stored.length === width * height) return stored;
    if (compact) stored = compact();
    const map = rows();
    assert.equal(map.length,height);
    const full = [];
    for (let y=0; y<height; y++) {
        gridPixel(stored, () => map, y * width + 1);
        const offset = (Number(map[y]) - 1) * width;
        full.push(...stored.slice(offset, offset + width));
    }
    return full;
}
module.exports = {gridPixel, logicalGrid};
