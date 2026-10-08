import assert from 'node:assert/strict'
import React from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {createServer} from 'vite'

// Uses a real plan produced by the backend engine when available (PLAN_JSON), otherwise a minimal fixture.
const server=await createServer({server:{middlewareMode:true},appType:'custom'})
try{
  const {default:Migration}=await server.ssrLoadModule('/src/Migration.jsx')
  const fs=await import('node:fs')
  const plan=JSON.parse(fs.readFileSync(process.env.PLAN_JSON||'scripts/fixtures/plan.json','utf8'))
  const props={openProfile:()=>{},plan,loading:false,error:'',profile:{occupation:'Mechatronics Engineer',location:'Brisbane, QLD',visa:'Student visa (subclass 500)',visaExpiry:'2027-02-28'},setProfile:()=>{},circumstances:{},setCircumstances:()=>{},activeId:null,setActiveId:()=>{},checks:{},toggleCheck:()=>{},onJobsAction:()=>{},jobs:null,onRefresh:()=>{},sample:true}
  const html=renderToStaticMarkup(React.createElement(Migration,props))
  for(const text of ['Your road to permanent residence','Independent','Employer sponsored','Your next steps','Compare routes','Decision support, not migration advice','Answer in Profile']) assert.ok(html.includes(text),text)
  assert.ok(!/\d+% (?:chance|fit|probability)/.test(html),'no fabricated probabilities')
  for(const bad of ['Previously held a 485','Exceptional international record','Category 2']) assert.ok(!html.includes(bad),bad)
  assert.ok(!plan.strategies.some(s=>s.id==='186-de'),'Direct Entry is ruled out for a 485 graduate')
  const empty=renderToStaticMarkup(React.createElement(Migration,{...props,plan:null,error:'Planner offline'}))
  assert.ok(empty.includes('Planner offline')&&empty.includes('Retry'))
  const settled=renderToStaticMarkup(React.createElement(Migration,{...props,plan:{...plan,strategies:[],context:{...plan.context,settled:true},headline:{title:'No migration pathway needed',detail:'Permanent'}}}))
  assert.ok(settled.includes('No migration pathway needed')&&!settled.includes('Your next steps'))
  assert.ok(!html.includes('Your circumstances')&&!html.includes('liveSrc'),'answers live in Profile and sources in the header')
  console.log(`Migration rendering checks passed: ${plan.strategies.length} strategies, offline state, settled state, no duplicate answers form.`)
}finally{await server.close()}
