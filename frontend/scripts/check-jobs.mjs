import assert from 'node:assert/strict'
import React from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {createServer} from 'vite'

const server=await createServer({server:{middlewareMode:true},appType:'custom'})
try{
  const {default:Jobs}=await server.ssrLoadModule('/src/Jobs.jsx')
  const profile={occupation:'Mechatronics Engineer',location:'Brisbane, QLD',experienceYears:1,skills:['Python'],roleCandidates:[{title:'Automation Engineer'}]}
  const render=jobs=>renderToStaticMarkup(React.createElement(Jobs,{jobs,profile,onSearch:()=>{}}))
  const missing=render({status:'not_configured',count:null,roles:[],note:'Connect Apify to collect adverts.'})
  assert.ok(missing.includes('Market evidence is not available yet'))
  assert.ok(!missing.includes('0 named employers'))
  assert.ok(missing.includes('Related roles from your profile'))
  const pending=render({status:'loading',collectionState:'running',count:null,roles:[],note:'Collecting this role and location.'})
  assert.ok(pending.includes('Collecting adverts for this search'))
  assert.ok(!pending.includes('No adverts at this level'))
  const market={count:0,levels:['Junior','Mid level','Senior','Leadership','Unspecified'].map(level=>({level,count:0})),companies:[],companyCount:0,unknownCompanyCount:0,skills:[],describedCount:0,salaryDisclosedCount:0,salaries:[],experienceExamples:[],juniorDemand:{count:0,totalJunior:0,examples:[]},aiMentions:{count:0,examples:[]}}
  const query={role:'Mechatronics Engineer',location:'Brisbane, QLD, Australia',dateWindow:'anyTime'}
  const empty=render({status:'fresh',count:0,query,roles:[],market:{all:market,byLevel:{}},note:'No adverts in this collection.'})
  assert.ok(empty.includes('No adverts at this level in the collected sample'))
  assert.ok(empty.includes('Salary')||empty.includes('salary'))
  assert.ok(empty.includes('not treated as zero'))
  const job={id:'test',title:'Junior Engineer',url:'https://jobs.example.org/1',company:'Test employer',location:'Brisbane',salary:'AUD 90,000 per year',seniority:{level:'Junior',basis:'Advert title',evidence:'Junior Engineer'},reason:'Your Python skill is mentioned.',fit:{label:'Stretch',supportedSkills:['Python'],notEvidencedSkills:['PLC'],explanation:'Review the actual requirements.'},experienceRequirement:{minimum:3,evidence:'Minimum 3 years of experience required.'},skillMentions:[{skill:'Python',evidence:'Python skills required.'}]}
  const known=render({status:'stale',count:1,query,collectedAt:'2026-10-01T12:00:00Z',roles:[job],market:{all:{...market,count:1,companyCount:1,companies:[{name:'Test employer',count:1}],salaryDisclosedCount:1,salaries:[{currency:'AUD',period:'year',basis:'Excludes super',count:1,min:90000,max:110000}],juniorDemand:{count:1,totalJunior:1,examples:[{title:job.title,url:job.url,evidence:job.experienceRequirement.evidence}]}},byLevel:{}},note:'Older sample. Not the total number of vacancies.'})
  for(const text of ['Stretch','Python','PLC','Test employer','90,000 to 110,000','Excludes super','Minimum 3 years','AI caused a change','Qualifications, licences and work rights','href="https://jobs.example.org/1"']) assert.ok(known.includes(text),text)
  assert.ok(!known.includes('% fit'))
  console.log('Jobs rendering checks passed: pending, unconfigured, valid zero, seniority, employers, salary bases, fit evidence and sample limitations.')
}finally{await server.close()}
