import assert from 'node:assert/strict'
import React from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {createServer} from 'vite'

// Uses a real plan produced by the backend engine when available (PLAN_JSON), otherwise a minimal fixture.
const server=await createServer({server:{middlewareMode:true},appType:'custom'})
try{
  const {default:Migration,MigrationSummaryCard}=await server.ssrLoadModule('/src/Migration.jsx')
  const fs=await import('node:fs')
  const plan=JSON.parse(fs.readFileSync(process.env.PLAN_JSON||'scripts/fixtures/plan.json','utf8'))
  const props={plan,loading:false,error:'',profile:{occupation:'Mechatronics Engineer',location:'Brisbane, QLD',visa:'Student visa (subclass 500)',visaExpiry:'2027-02-28'},setProfile:()=>{},circumstances:{},setCircumstances:()=>{},activeId:null,setActiveId:()=>{},checks:{},toggleCheck:()=>{},onJobsAction:()=>{},jobs:null,onRefresh:()=>{},sample:true}
  const html=renderToStaticMarkup(React.createElement(Migration,props))
  for(const text of ['Your road to permanent residence','Independent','Employer sponsored','Your next steps','Compare routes','Decision support, not migration advice','sample answers']) assert.ok(html.includes(text),text)
  assert.ok(!/\d+% (?:chance|fit|probability)/.test(html),'no fabricated probabilities')
  for(const bad of ['Previously held a 485','Exceptional international record','Category 2']) assert.ok(!html.includes(bad),bad)
  assert.ok(!plan.strategies.some(s=>s.id==='186-de'),'Direct Entry is ruled out for a 485 graduate')
  const empty=renderToStaticMarkup(React.createElement(Migration,{...props,plan:null,error:'Planner offline'}))
  assert.ok(empty.includes('Planner offline')&&empty.includes('Retry'))
  const settled=renderToStaticMarkup(React.createElement(Migration,{...props,plan:{...plan,strategies:[],context:{...plan.context,settled:true},headline:{title:'No migration pathway needed',detail:'Permanent'}}}))
  assert.ok(settled.includes('No migration pathway needed')&&!settled.includes('Your next steps'))
  const card=renderToStaticMarkup(React.createElement(MigrationSummaryCard,{plan,activeId:null,onOpen:()=>{}}))
  assert.ok(card.includes('Permanent residence roadmap')&&card.includes(plan.strategies[0].name.replace('&','&amp;').replace("'",'&#x27;')))
  console.log(`Migration rendering checks passed: ${plan.strategies.length} strategies, offline state, settled state and overview card.`)
}finally{await server.close()}
