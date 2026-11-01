const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx=vm.createContext({console});vm.runInContext(fs.readFileSync('dist/vendor/vue.js','utf8'),ctx);
ctx.template=fs.readFileSync('dist/index.html','utf8').split('<body>')[1].split('<script src=')[0];
assert.ok(!/&[a-zA-Z]+;/.test(ctx.template),'Identity entity decoding is only valid when the template has no named entities');
vm.runInContext('Vue.compile(template,{decodeEntities:s=>s})',ctx);
for(const file of ['dist/verify.js','dist/quality.js','dist/quality-view.js','dist/workbench.js','dist/analysis-advanced.js'])new vm.Script(fs.readFileSync(file,'utf8'),{filename:file});
console.log('PASS: actual Vue template compiles and changed browser scripts parse; this is not a rendered browser visual check');
