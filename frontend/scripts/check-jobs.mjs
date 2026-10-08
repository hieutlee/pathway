import assert from 'node:assert/strict'
import React from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {createServer} from 'vite'

const server=await createServer({server:{middlewareMode:true},appType:'custom'})
try{
  const {default:Jobs,prettyLocation}=await server.ssrLoadModule('/src/Jobs.jsx')
  const profile={occupation:'Mechatronics Engineer',location:'Brisbane, QLD',experienceYears:1,skills:['Python'],roleCandidates:[{title:'Mechatronics Engineer'},{title:'Controls Engineer'}]}
  const render=jobs=>renderToStaticMarkup(React.createElement(Jobs,{jobs,profile,onSearch:()=>{}}))
  const empty=render(null)
  assert.ok(empty.includes('Suggested from your resume')&&empty.includes('Controls Engineer'))
  assert.ok(/name="?"?[^>]*value=""/.test(empty)||empty.includes('placeholder="e.g. Mechatronics Engineer"'),'role is suggested, not prefilled')
  assert.ok(empty.includes('Brisbane, Queensland'),'location shown without country')
  assert.ok(empty.includes('Latest (24 hours)')&&empty.includes('Last week')&&!empty.includes('Any time'))
  assert.equal(prettyLocation('Brisbane, QLD, Australia'),'Brisbane, Queensland')
  assert.equal(prettyLocation('Sydney, NSW'),'Sydney, New South Wales')
  const lv=['Junior','Mid level','Senior','Leadership','Unspecified']
  const ms=(n)=>({count:n,levels:lv.map(level=>({level,count:level==='Junior'?n:0})),companies:[],companyCount:1,unknownCompanyCount:0,
    skills:[{skill:'PLC',count:2,examples:[{title:'Controls Engineer',company:'A',url:'https://x.example/1',evidence:'PLC programming required'}]},{skill:'SCADA',count:1,examples:[]}],
    describedCount:n,salaryDisclosedCount:0,salaries:[],experienceExamples:[],juniorDemand:{count:0,totalJunior:0,examples:[]},aiMentions:{count:0,examples:[]},
    workRights:{counts:{citizen_pr:1,clearance:0,no_sponsorship:0,sponsorship:0,work_rights:0,not_stated:1},examples:[]}})
  const job=(id,tier,label)=>({id,title:`Role ${id}`,url:`https://x.example/${id}`,company:`Co ${id}`,location:'Brisbane, Queensland, Australia',seniority:{level:'Junior'},
    fit:{label:'Good match',haveCount:1,transferableCount:1,gapCount:0,reasons:['1 of 2 advertised skills are on your resume.'],eligibility:{tier,label,reason:'r',evidence:'Applicants must be Australian Citizens'},
      skills:[{skill:'PLC',status:'have',reason:'Project · Pump Station mentions PLC.'},{skill:'SCADA',status:'transferable',reason:'Transferable: Project shows WinCC, which builds SCADA platforms.'}]}})
  const html=render({status:'fresh',count:2,query:{role:'Controls Engineer',location:'Brisbane, QLD, Australia',dateWindow:'pastWeek'},collectedAt:'2026-10-08T00:00:00Z',
    roles:[job(1,0,'No restriction stated'),job(2,2,'Citizens or PR only')],market:{all:ms(2),byLevel:{Junior:ms(2),'Mid level':ms(0),Senior:ms(0)}},
    skillStatus:{PLC:{status:'have',reason:'Project · Pump Station mentions PLC.'},SCADA:{status:'transferable',reason:'Transferable'}},note:'2 adverts'})
  for(const t of ['What employers ask for in Controls Engineer adverts','Mid-level','You can apply','Citizens, PR or clearance only','Transferable: Project shows WinCC','skillChip have','skillChip transferable','Who can apply']) assert.ok(html.includes(t),t)
  for(const t of ['Who is hiring','Leadership']) assert.ok(!html.includes(t),t)
  console.log('Jobs rendering checks passed: suggested role, Australian locations, date windows, level filter, market chart, eligibility groups and reasoned skill chips.')
}finally{await server.close()}
