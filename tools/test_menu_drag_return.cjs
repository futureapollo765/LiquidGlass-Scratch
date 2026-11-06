#!/usr/bin/env node
/** Drag open panels through their press origin using the native green-flag loop. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {scene} = require('./test_stretch_gesture.cjs');

const [archive, output] = process.argv.slice(2);
if (!output) throw Error('Usage: node test_menu_drag_return.cjs Studio.sb3 report.json');
const owner = 3;
const path = 'Background';
const report = {archive, observations: []};

function near(value, expected, label) {
    assert.ok(Math.abs(value - expected) < .2, `${label}: expected ${expected}, got ${value}`);
}

async function run(compiler) {
    const s = await scene(compiler, {filename: archive});
    const slot = name => s.get(name)[owner - 1];
    function panel(child) {
        if (!child) return s.pose(owner);
        const index = s.get('UI layer path').indexOf(path);
        assert.ok(index >= 0, 'The selected submenu must continue to exist');
        return Object.fromEntries(['x','y','w','h','rows'].map(name =>
            [name, Number(s.get('UI layer ' + name)[index])]));
    }
    function click(x,y) {
        s.mouse(x,y,true); s.frame(2);
        s.mouse(x,y,false); s.frame();
    }
    function checkPanel(child) {
        const before = panel(child);
        const rows = child ? before.rows + 1 : Number(slot('UI expanded height')) / Number(slot('UI row height'));
        const x = Math.round(before.x - 14), y = Math.round(before.y + before.h/2 - before.h/(2*rows));
        s.mouse(x,y,false); s.frame(2); s.mouse(x,y,true); s.frame(20);
        const base = panel(child), parent = panel(false), event = Number(s.get('UI event number'));
        const layer = child ? s.get('UI layer path').indexOf(path) + 1 : 0;
        function sample(dx,dy) {
            s.mouse(x+dx,y+dy,true); s.frame(20);
            assert.equal(Number(s.get('UI pressed id')), owner);
            assert.equal(Number(s.get('UI pressed layer')), layer);
            assert.equal(slot('UI contact path'), child ? path : '');
            assert.equal(Number(slot('UI open')), 1);
            if (child) {
                const under = panel(false);
                for (const key of ['x','y','w','h']) near(under[key],parent[key],'Underlying menu ' + key);
            }
            return panel(child);
        }
        const far = sample(64,44), partial = sample(18,12), neutral = sample(0,0);
        const opposite = sample(-64,-44), horizontal = sample(-64,0);
        for (const key of ['w','h']) {
            assert.ok(far[key] > partial[key]+2 && partial[key] > base[key]+2,
                `Held ${child ? path : 'root'} ${key} must shrink toward its press size: ${[base[key],far[key],partial[key]]}`);
            near(neutral[key],base[key],'Panel dimensions at the original press point');
            near(opposite[key],far[key],'Equal extensions to opposite sides');
        }
        for (const key of ['x','y']) {
            near(neutral[key],base[key],'Held center returns to the press origin');
            assert.ok(far[key] > base[key]+2 && opposite[key] < base[key]-2, 'Panel follows both drag directions');
        }
        near(horizontal.w,opposite.w,'Keeping horizontal displacement keeps its width');
        near(horizontal.h,base.h,'Returning only vertically restores the height');
        s.mouse(x-64,y,false); s.frame(40);
        assert.equal(Number(s.get('UI event number')),event,'Dragging across a row must not activate it');
        assert.equal(Number(slot('UI open')),1);
        assert.equal(slot('UI page'),child ? path : '');
        report.observations.push({compiler, panel:child ? path : 'root', size:
            [base,far,partial,neutral,opposite,horizontal].map(p=>[p.w,p.h])});
    }
    try {
        const launcher = panel(false);
        click(launcher.x,launcher.y); s.frame(50);
        checkPanel(false);
        const root = panel(false);
        const row = s.get('UI row path').findIndex((value,i) => value === path && Number(s.get('UI row layer')[i]) === 0);
        assert.ok(row >= 0);
        const pitch = Number(slot('UI row height')) * root.h / Number(slot('UI expanded height'));
        click(root.x,root.y + root.h/2 - (Number(s.get('UI row index')[row])+.5)*pitch); s.frame(60);
        assert.equal(slot('UI page'),path);
        checkPanel(true);
        const child = panel(true);
        click(child.x, child.y + child.h/2 - child.h/(2*(child.rows+1))); s.frame(65);
        assert.equal(slot('UI page'),'');
        assert.equal(s.get('UI layer path').includes(path),false);
        assert.equal(Number(slot('UI open')),1);
    } finally {
        s.vm.stopAll();
    }
}

(async () => {
    for (const compiler of [true,false]) await run(compiler);
    report.passed = true;
})().catch(e => { report.passed=false; report.error=String(e.stack || e); }).finally(() => {
    fs.writeFileSync(output, JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
    process.exit(report.passed ? 0 : 1);
});
