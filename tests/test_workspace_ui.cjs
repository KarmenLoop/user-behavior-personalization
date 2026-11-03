// Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
// Focused DOM harness: execute the shipped render/language/vote functions without a provider.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function workspace() {
  const ids = new Map();
  class Element {
    constructor(tag) { this.tagName = tag; this.children = []; this.listeners = {}; this.value = ''; this.textContent = ''; this.classList = {toggle(){}}; }
    set id(value) { this._id = value; ids.set(value, this); }
    get id() { return this._id; }
    append(...nodes) { this.children.push(...nodes); }
    replaceChildren(...nodes) {
      const remove = node => { if (node.id && ids.get(node.id) === node) ids.delete(node.id); node.children.forEach(remove); };
      this.children.forEach(remove); this.children = []; this.append(...nodes);
    }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    async dispatch(name) { if (this.listeners[name]) await this.listeners[name]({target:this}); }
    setAttribute() {}
    removeAttribute() {}
  }
  const document = {
    createElement: tag => new Element(tag),
    getElementById: id => { if (!ids.has(id)) { const node = new Element('div'); node.id = id; } return ids.get(id); },
    querySelector: () => ({content:'test'}), querySelectorAll: () => [],
    documentElement: {}, body: new Element('body')
  };
  let source = fs.readFileSync('web/app.js', 'utf8');
  // Keep actual functions; omit only page-start event bindings and automatic network startup.
  source = source.slice(0, source.indexOf("document.querySelectorAll('[data-view]')")) +
    source.slice(source.indexOf('function conditionsText'), source.indexOf("$('semantic-learn').addEventListener"));
  const context = vm.createContext({document, localStorage:{getItem:()=>null}, crypto:{randomUUID:()=> 'test-id'}, setTimeout, console});
  vm.runInContext(source, context);
  vm.runInContext(`
    state.boot={paused:false,revision:1,model_enabled:true,configured_model:'test-model'};
    render=()=>{renderModelControls();renderAnswers();};
    const submissions=[];
    write=async(name,args)=>{submissions.push({name,args});return {};};
    refresh=async()=>{};
  `, context);
  return {context, document, run: code => vm.runInContext(code,context)};
}
function record(id='comparison-one', revision=1, feedback=null) {
  return {comparison_id:id,revision,model:'test-model',created_at:'2026-11-04T00:00:00Z',task_conditions:{},answers:{a:'Actual A',b:'Actual B'},revealed:!!feedback,mapping:{a:'baseline',b:'personalized'},selected_preferences:[],execution_metadata:{},feedback};
}
function buttons(node) { return [node,...node.children.flatMap(buttons)].filter(node=>node.tagName==='button'); }

for (const revised of [false,true]) test(`${revised?'revised':'first'} vote preserves accuracy choices through language switches`, async () => {
  const app = workspace();
  app.context.record = record('comparison-one',1,revised?{accuracy_a:'reported_incorrect',accuracy_b:'reported_correct',choice:'b',blinded:true}:null);
  app.run('state.comparison=record;renderAnswers();');
  const a=app.document.getElementById('accuracy-a'), b=app.document.getElementById('accuracy-b');
  a.value='reported_correct';await a.dispatch('change');b.value='reported_incorrect';await b.dispatch('change');
  app.run("language='zh';setLanguage();language='en';setLanguage();language='zh';setLanguage();");
  assert.equal(app.document.getElementById('accuracy-a').value,'reported_correct');
  assert.equal(app.document.getElementById('accuracy-b').value,'reported_incorrect');
  const vote=buttons(app.document.getElementById('actual-result')).find(node=>node.textContent==='更喜欢 A');
  await vote.dispatch('click');
  const submitted=app.run('submissions[0]');
  assert.equal(submitted.name,'profile_comparison_vote');
  assert.equal(submitted.args.accuracy_a,'reported_correct');assert.equal(submitted.args.accuracy_b,'reported_incorrect');assert.equal(submitted.args.choice,'a');
});

test('comparison change, revision invalidation, pause and deletion clear accuracy drafts', async () => {
  const app=workspace();
  const selectDraft=async()=>{app.document.getElementById('accuracy-a').value='reported_correct';await app.document.getElementById('accuracy-a').dispatch('change');};
  app.context.first=record();app.run('state.comparison=first;renderAnswers();');await selectDraft();
  app.context.next=record('comparison-two');app.run('state.comparison=next;renderAnswers();');assert.equal(app.document.getElementById('accuracy-a').value,'not_checked');
  await selectDraft();app.context.changed=record('comparison-two',2);app.run('state.comparison=changed;renderAnswers();');assert.equal(app.document.getElementById('accuracy-a').value,'not_checked');
  await selectDraft();app.run('state.boot.paused=true;renderAnswers();state.boot.paused=false;renderAnswers();');assert.equal(app.document.getElementById('accuracy-a').value,'not_checked');
  await selectDraft();app.run('clearAnswers();state.comparison=changed;renderAnswers();');assert.equal(app.document.getElementById('accuracy-a').value,'not_checked');
  await selectDraft();app.run('state.comparison=null;renderAnswers();state.comparison=changed;renderAnswers();');assert.equal(app.document.getElementById('accuracy-a').value,'not_checked');
});

test('completed, failed and running job states localize on language rerender', async () => {
  const app=workspace();
  await app.run("state.job={context:'writing',kind:'compare'};pollModelJob(state.job,{status:'completed',result:{}})");
  app.run("language='zh';setLanguage();");
  assert.equal(app.document.getElementById('model-job-state').textContent,'模型请求已完成。');
  app.run("language='en';finishJobError({}, {code:'MODEL_FAILURE',message:'Provider diagnostic'});language='zh';setLanguage();");
  assert.equal(app.document.getElementById('model-job-state').textContent,'模型请求失败 · MODEL_FAILURE');
  app.run("language='en';state.job={context:'writing',kind:'compare'};renderModelControls();language='zh';setLanguage();");
  for(const id of ['model-job-state','semantic-job-state'])assert.equal(app.document.getElementById(id).textContent,'模型请求正在运行；仍可暂停或刷新。 · test-model');
});


test('default proposal review shows exact server peers before approval and labels updates bilingually', async () => {
  const app=workspace();
  app.run(`state.portrait={confirmed_preferences:[{id:'peer',statement:'Keep it brief.',scope:'writing',conditions:{stage:'draft'}}],pending_preferences:[{id:'proposal',statement:'Give detailed explanations.',scope:'writing',conditions:{stage:'draft'},dimension:'response_length',value:'detailed',evidence:[],approval_replacements:{'':[{id:'peer',statement:'Keep it brief.',scope:'writing',conditions:{stage:'draft'}}],peer:[{id:'peer',statement:'Keep it brief.',scope:'writing',conditions:{stage:'draft'}}]}}]};state.boot.sources=[];renderProposals();`);
  const text=node=>[node.textContent,...node.children.map(text)].join(' ');
  assert.match(text(app.document.getElementById('proposals')),/peer · Keep it brief. · writing/);
  assert.match(text(app.document.getElementById('proposals')),/Update existing preferences/);
  assert.match(text(app.document.getElementById('proposals')),/Approve update/);
  app.run("language='zh';renderProposals();");
  assert.match(text(app.document.getElementById('proposals')),/确认更新/);
  assert.doesNotMatch(text(app.document.getElementById('proposals')),/保存为单独的偏好/);
  await buttons(app.document.getElementById('proposals')).find(node=>node.textContent==='确认更新').dispatch('click');
  const submitted=app.run('submissions[0]');
  assert.equal(submitted.name,'profile_proposal_review');assert.equal(submitted.args.proposal_id,'proposal');
  assert.equal(submitted.args.decision,'accept');assert.equal(submitted.args.replace_rule_id,undefined);
  app.run("state.portrait.pending_preferences[0].approval_replacements['']=[];renderProposals();");
  assert.match(text(app.document.getElementById('proposals')),/保存为单独的偏好/);
});

test('count notices and comparison deletion tooltips follow the selected language', async () => {
  const app=workspace();
  await app.run("state.job={context:'writing',kind:'learn'};pollModelJob(state.job,{status:'completed',result:{added_proposals:3}})");
  app.run("language='zh';setLanguage();");
  assert.equal(app.document.getElementById('notice').textContent,'新增待审核提案：3');
  app.run("language='en';setLanguage();");
  assert.equal(app.document.getElementById('notice').textContent,'Pending proposals added: 3');
  app.context.record=record();app.run('state.comparison=record;renderAnswers();');
  assert.match(buttons(app.document.getElementById('actual-result')).find(node=>node.textContent==='Forget').title,/comparison.*private answers/);
  app.run("language='zh';setLanguage();");
  assert.equal(buttons(app.document.getElementById('actual-result')).find(node=>node.textContent==='遗忘').title,'删除本次对比的私有回答、执行元数据和反馈。');
});
