import assert from 'node:assert/strict'
import React from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {createServer} from 'vite'
import fs from 'node:fs'

const server=await createServer({server:{middlewareMode:true},appType:'custom'})
try {
  const {default:Home,JobResults}=await server.ssrLoadModule('/src/Overview.jsx')
  const plan=JSON.parse(fs.readFileSync('scripts/fixtures/plan.json','utf8'))
  const profile={occupation:'Mechatronics Engineer',location:'Brisbane, QLD'}
  const render=(data,p=plan)=>renderToStaticMarkup(React.createElement(Home,{data,profile,plan:p,planLoading:false,activeId:null,checks:{},toggleCheck:()=>{},setActiveTab:()=>{},onJobsAction:()=>{},openProfile:()=>{}}))
  const html=render({jobs:{status:'not_configured',count:null,roles:[],note:'Connection required.'}})
  const next=plan.strategies[0].milestones.find(m=>m.status!=='done')
  for(const text of ['Your next step',next.title,'Visa days left','Points today','Matching jobs','Not collected','Next steps','Roles for you']) assert.ok(html.includes(text.replace("'",'&#x27;')),text)
  for(const removed of ['Profile checklist','Invitation evidence','Occupation shortage','Build Evidence Plan','Current blockers','Your pathway map']) assert.ok(!html.includes(removed),removed)
  const withMissing=render({},{...plan,missing:[{field:'dob',label:'Date of birth'}]})
  assert.ok(withMissing.includes('1 answer would sharpen your plan'))
  const listing=renderToStaticMarkup(React.createElement(JobResults,{jobs:{status:'fresh',count:1,roles:[{title:'Test Engineer',company:'Example Co',location:'QLD',url:'https://jobs.example.org/123',reason:'Skills mentioned: C++.'}],note:''},limit:3}))
  assert.ok(listing.includes('href="https://jobs.example.org/123"')&&!listing.includes('82%'))
  console.log('Home rendering checks passed: one next step, three numbers, next steps, top jobs, no repeated cards.')
} finally {
  await server.close()
}
