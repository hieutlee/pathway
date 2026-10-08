import assert from 'node:assert/strict'
import React from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {createServer} from 'vite'

const server=await createServer({server:{middlewareMode:true},appType:'custom'})
try{
  const {ResumeReview,Landing,SAMPLE_RESUME,unionMonths,fmtMonths}=await server.ssrLoadModule('/src/ResumeReview.jsx')
  const html=renderToStaticMarkup(React.createElement(ResumeReview,{initialResume:SAMPLE_RESUME,profile:{visa:'Student visa (subclass 500)'},fileName:'cv.pdf',catalogue:[],onBack:()=>{},onConfirm:()=>{}}))
  for(const text of ['Check what we found','Work experience','Volunteering','not counted as work experience','Projects','Achievements','Your target occupation','Mechatronics Engineer','Engineers Australia','Paid experience','Relevant, after graduating','Looks right, build my plan']) assert.ok(html.includes(text),text)
  for(const bad of ['ANZSCO code','OSCA code','Career goal']) assert.ok(!html.includes(bad),bad)
  // overlapping roles are counted once; volunteering is not part of experience
  assert.equal(unionMonths([{start:'2024-01-01',end:'2024-06-01'},{start:'2024-04-01',end:'2024-12-01'}]),12)
  assert.equal(unionMonths([{start:'2024-01-01',end:'2024-12-01'}],'2024-06-01'),6)
  assert.equal(fmtMonths(0),'None yet'); assert.equal(fmtMonths(27),'2 yrs 3 mos')
  const landing=renderToStaticMarkup(React.createElement(Landing,{onFile:()=>{},onDemo:()=>{},busy:false,error:'',fileName:'',saved:null,onResume:()=>{}}))
  assert.ok(landing.includes('Drop your resume here')&&landing.includes('Check what we found'))
  console.log('Review rendering checks passed: sections, no code inputs, duration union, post-graduation counting and landing.')
}finally{await server.close()}
