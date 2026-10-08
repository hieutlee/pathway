import assert from 'node:assert/strict'
import React from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {createServer} from 'vite'

const server=await createServer({server:{middlewareMode:true},appType:'custom'})
try {
  const {default:Overview}=await server.ssrLoadModule('/src/Overview.jsx')
  const profile={occupation:'Test Engineer',location:'Brisbane, QLD'}
  const recommendation={profileCompleteness:{completed:0,total:8,checks:[{id:'occupation',label:'Target occupation',present:false}],explanation:'Counts supplied fields only.'}}
  const render=data=>renderToStaticMarkup(React.createElement(Overview,{data,profile,setActiveTab:()=>{},onUpgrade:()=>{}}))
  const missing=render({recommendation,jobs:{status:'not_configured',count:null,roles:[],note:'Connection required.'},migration:{status:'unavailable',note:'Tables unavailable.'},occupation:{status:'unavailable',shortageNote:'Workbook unavailable.'}})
  assert.ok(missing.includes('0 of 8'))
  assert.ok(missing.includes('Not connected'))
  assert.ok(missing.includes('Tables unavailable.'))
  assert.ok(missing.includes('Workbook unavailable.'))
  for(const placeholder of ['Pathway readiness','Current OSL checked','Current round published','% fit','+18']) assert.ok(!missing.includes(placeholder))
  const good=render({recommendation,jobs:{status:'fresh',count:0,scannedCount:100,roles:[],note:'No matching listings.'},migration:{latestRound:{date:'4 June 2026',invitations:10000,minimumPoints:95,matchedOccupation:'Test Engineer'},occupationNote:'Historical result only.'},occupation:{oslYear:2025,occupationResult:{occupation:'Test Engineer',classification:'ANZSCO',code:'233999',nationalRating:'No shortage',state:'QLD',stateRating:'Regional shortage',stateRatings:{QLD:'Regional shortage',NSW:'No shortage'}}}})
  assert.ok(good.includes('No matches in this collection'))
  assert.ok(good.includes('95 points'))
  assert.ok(good.includes('10,000'))
  assert.ok(good.includes('Regional shortage'))
  assert.ok(good.includes('No shortage'))
  const listing=render({jobs:{status:'partial',count:1,scannedCount:1,roles:[{title:'Test Engineer',company:'Example Co',location:'QLD',url:'https://jobs.example.org/123',matchedSkills:['C++'],reason:'Skills mentioned: C++.'}]}})
  assert.ok(listing.includes('href="https://jobs.example.org/123"'))
  assert.ok(listing.includes('collection time is unknown'))
  assert.ok(listing.includes('Skills mentioned: C++.'))
  assert.ok(!listing.includes('82%'))
  console.log('Overview rendering checks passed: missing data, zero count, official facts and real listing links.')
} finally {
  await server.close()
}
