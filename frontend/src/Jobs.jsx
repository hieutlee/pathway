import React, {useEffect, useState} from 'react'
import {Search, BriefcaseBusiness, Building2, ArrowUpRight, ExternalLink, LoaderCircle, Clock3, FileText, Check, CircleHelp} from 'lucide-react'
import {dateLabel, SourceFooter} from './Overview'

const levels=['Junior','Mid level','Senior','Leadership','Unspecified']
const money=n=>Number(n).toLocaleString('en-AU',{maximumFractionDigits:0})

function EvidenceLink({item}){
  return <a className="jobEvidenceLink" href={item.url} target="_blank" rel="noreferrer"><span>{item.evidence}</span><small>{item.title}<ExternalLink size={12}/></small></a>
}

export function FitCard({job}){
  const fit=job.fit||{}, requirement=job.experienceRequirement
  return <article className="card fitCard">
    <div className="fitCardTop"><div><span className="kicker">{job.company||'Employer not supplied'}</span><h3><a href={job.url} target="_blank" rel="noreferrer">{job.title}<ArrowUpRight size={17}/></a></h3><p>{job.location||'Location not supplied'}</p></div><span className={`fitLabel ${fit.label==='Stretch'?'stretch':''}`}>{fit.label||'Needs review'}</span></div>
    <div className="advertFacts">{job.workRights&&job.workRights.category!=='not_stated'&&<span className={`wrBadge ${job.workRights.category}`} title={job.workRights.evidence}>{job.workRights.label}</span>}<span>{job.seniority.level}</span><span>{job.salary||'Salary not disclosed'}</span><span>{job.postedAt?`Posted ${dateLabel(job.postedAt)}`:'Advert date unavailable'}</span></div>
    <p className="fitReason">{job.reason}</p>
    <div className="fitColumns"><div><b><Check size={14}/> Evidence in your profile</b><p>{fit.supportedSkills?.join(', ')||'No skill overlap detected in the available text.'}</p></div><div><b><CircleHelp size={14}/> Check or add evidence</b><p>{fit.notEvidencedSkills?.slice(0,8).join(', ')||'Review the full advert for qualifications, licences and other requirements.'}</p></div></div>
    <details className="advertEvidence"><summary>Why this assessment?</summary><p>{fit.explanation}</p>{job.workRights?.evidence&&<p><b>Work rights:</b> {job.workRights.evidence}</p>}<p><b>Seniority:</b> {job.seniority.basis}. {job.seniority.evidence}</p>{requirement&&<blockquote>{requirement.evidence}</blockquote>}{job.skillMentions?.slice(0,6).map(s=><p key={s.skill}><b>{s.skill}:</b> {s.evidence}</p>)}<a href={job.url} target="_blank" rel="noreferrer">Read the full advert <ExternalLink size={12}/></a></details>
  </article>
}

export default function Jobs({jobs,profile,onSearch,disabled=false}){
  const [role,setRole]=useState(jobs?.query?.role||profile.occupation||'')
  const [location,setLocation]=useState(jobs?.query?.location||profile.location||'Australia')
  const [window,setWindow]=useState(jobs?.query?.dateWindow||'anyTime')
  const [level,setLevel]=useState('All levels')
  const [submitting,setSubmitting]=useState(false)
  useEffect(()=>{if(jobs?.query){setRole(jobs.query.role);setLocation(jobs.query.location);setWindow(jobs.query.dateWindow)}setLevel('All levels')},[jobs?.queryId])
  const available=typeof jobs?.count==='number'&&jobs?.market
  const collecting=['running','starting','checking_cache'].includes(jobs?.collectionState)||jobs?.status==='loading'
  const market=available?(level==='All levels'?jobs.market.all:jobs.market.byLevel[level]):null
  const roles=(jobs?.roles||[]).filter(j=>level==='All levels'||j.seniority.level===level)
  const related=[...new Set((profile.roleCandidates||[]).map(r=>typeof r==='string'?r:r.title).filter(r=>r&&r.toLowerCase()!==role.toLowerCase()))].slice(0,4)
  const gapCounts={}
  for(const job of roles) for(const skill of job.fit?.notEvidencedSkills||[]) gapCounts[skill]=(gapCounts[skill]||0)+1
  const gaps=Object.entries(gapCounts).sort((a,b)=>b[1]-a[1]).slice(0,5)
  async function search(event,searchRole=role){
    event?.preventDefault();setSubmitting(true)
    try{await onSearch({role:searchRole.trim(),location:location.trim(),dateWindow:window})}finally{setSubmitting(false)}
  }
  return <div className="singleView jobsIntelligence">
    <div className="viewTitle"><span className="kicker">Your next role, informed by real adverts</span><h2>Find your fit. Understand the expectations.</h2><p>Explore employers, skills and pay for your desired role, then compare individual adverts with your reviewed resume profile.</p></div>
    <section className="card jobSearchCard"><form className="jobSearchForm" onSubmit={search}>
      <label>Desired role<input value={role} onChange={e=>setRole(e.target.value)} minLength={2} maxLength={160} required placeholder="Mechatronics Engineer"/></label>
      <label>Australian location<input value={location} onChange={e=>setLocation(e.target.value)} minLength={2} maxLength={160} required placeholder="Brisbane, QLD"/></label>
      <label>Advert date at collection<select value={window} onChange={e=>setWindow(e.target.value)}><option value="anyTime">Any time</option><option value="past24Hours">Past 24 hours</option><option value="pastWeek">Past week</option><option value="pastMonth">Past month</option></select></label>
      <button type="submit" className="primary" disabled={submitting||disabled}>{submitting?<LoaderCircle size={16} className="spin"/>:<Search size={16}/>}Explore role</button>
    </form><p className="jobSearchHint">Recent searches reuse collected adverts. A new search collects a small sample when collection is enabled.</p>
    {related.length>0&&<div className="relatedRoles"><span>Related roles from your profile</span>{related.map(title=><button type="button" key={title} disabled={disabled||submitting} onClick={()=>search(null,title)}>{title}<ArrowUpRight size={12}/></button>)}</div>}</section>

    <div className={`collectionBanner ${jobs?.status==='stale'?'older':''}`} aria-live="polite">{collecting?<LoaderCircle size={17} className="spin"/>:<Clock3 size={17}/>}<div><b>{collecting?'Collecting adverts for this search':available?`${jobs.query?.role||role} · ${jobs.query?.location||location}`:'Waiting for a usable collection'}</b><p>{jobs?.note||'Search for a role and location to begin.'}</p>{jobs?.collectedAt&&<small>Collected {dateLabel(jobs.collectedAt,true)} · {jobs.cached?'Reused collection':'Latest collection'} · One source · Search radius up to 25 miles (about 40 km)</small>}{jobs?.collectionNote&&<p>{jobs.collectionNote}</p>}{jobs?.seedNote&&<small>{jobs.seedNote}</small>}</div></div>

    {available?<>
      <section className="levelSection"><div className="sectionHeading"><div><span className="kicker">Experience levels in this sample</span><h3>Where are the opportunities?</h3></div><small>Select a level to update the insights and matches below.</small></div>
      <div className="levelCards">{['All levels',...levels].map(name=><button type="button" key={name} aria-pressed={level===name} className={level===name?'selected':''} onClick={()=>setLevel(name)}><span>{name}</span><b>{name==='All levels'?jobs.count:jobs.market.all.levels.find(l=>l.level===name)?.count||0}</b><small>adverts</small></button>)}</div>
      <p className="jobMethod">Level comes from explicit title, provider label or stated experience. Inferred levels use 0–2, 3–5 and 6+ years. Ambiguous labels such as “Mid-Senior level” stay unspecified unless other evidence resolves them.</p></section>

      <div className="marketEvidenceGrid">
        <section className="card marketSkills"><span className="kicker">{level} · {market.describedCount} descriptions available</span><h3>What employers mention</h3>{market.skills.length?<><div className="skillBars">{market.skills.map(s=><div key={s.skill}><span>{s.skill}</span><div className="skillTrack"><i style={{width:`${market.count?s.count/market.count*100:0}%`}}/></div><b>{s.count} / {market.count}</b></div>)}</div><p className="jobMethod">Advert mentions, using a starter skills vocabulary. Not every mention is a mandatory requirement. Open a match to read the supporting text.</p></>:<p className="dataHint">No supported skill mentions found for this selection. Review the adverts directly.</p>}</section>
        <section className="card"><span className="kicker">{level} · {market.companyCount} named employers</span><h3>Who is hiring?</h3>{market.companies.length?<div className="hiringCompanies">{market.companies.map(c=><div key={c.name}><Building2 size={16}/><span>{c.name}</span><b>{c.count}</b></div>)}</div>:<p className="dataHint">No employers identified for this selection.</p>}<p className="jobMethod">Counts refer to collected adverts. {market.unknownCompanyCount>0?`${market.unknownCompanyCount} adverts do not name an employer.`:''}</p></section>
        <section className="card"><span className="kicker">{level} · {market.salaryDisclosedCount} of {market.count} disclose pay</span><h3>Advertised salary ranges</h3>{market.salaries.length?<div className="salaryGroups">{market.salaries.map((s,i)=><div key={i}><strong>{s.currency} {money(s.min)}{s.max!==s.min?` to ${money(s.max)}`:''}<small> / {s.period}</small></strong><span>{s.basis} · {s.count} adverts</span></div>)}</div>:<p className="dataHint">No comparable salary ranges available. Missing pay or an unclear pay period is not treated as zero.</p>}<p className="jobMethod">Lowest to highest advertised endpoints. Different pay periods, currencies and super arrangements stay separate. This is not a market average.</p></section>
        <section className="card"><span className="kicker">Evidence, not assumptions</span><h3>What does this mean for your level?</h3>{market.experienceExamples.length?<>{market.experienceExamples.slice(0,2).map((item,i)=><EvidenceLink key={i} item={item}/>)}</>:<p className="dataHint">No explicit minimum experience requirement was reliably detected for this selection.</p>}
        <p className="observedFact">{market.aiMentions.count} of {market.count} adverts mention detected AI tools or machine learning skills.</p>{market.aiMentions.examples.slice(0,1).map((item,i)=><EvidenceLink key={i} item={item}/>)}
        {jobs.market.all.juniorDemand.count>0&&<><p className="observedFact">{jobs.market.all.juniorDemand.count} of {jobs.market.all.juniorDemand.totalJunior} junior adverts ask for at least 3 years in a stated area.</p>{jobs.market.all.juniorDemand.examples.slice(0,1).map((item,i)=><EvidenceLink key={i} item={item}/>)}</>}
        {market.workRights&&(()=>{const w=market.workRights.counts;const restricted=(w.citizen_pr||0)+(w.clearance||0);return <p className="observedFact">{restricted} of {market.count} adverts restrict to citizens/PR or need a security clearance; {w.sponsorship||0} mention visa sponsorship. The Migration tab uses this when ranking employer routes.</p>})()}
        <p className="jobMethod">One collection cannot establish a decline in junior hiring or show that AI caused a change in expectations.</p></section>
      </div>

      <section className="profileComparison"><FileText size={22}/><div><span className="kicker">Your reviewed profile</span><h3>{profile.experienceYears!==''&&profile.experienceYears!=null?`${profile.experienceYears} years of experience`:'Experience not supplied'} · {profile.skills?.length||0} supplied skills</h3><p>Matches below explain skill overlap and experience gaps. Review resume extraction before relying on these comparisons. Qualifications, licences and work rights still need to be checked.</p>{gaps.length>0&&<p><b>Evidence to strengthen:</b> {gaps.map(([skill,count])=>`${skill} (${count} adverts)`).join(', ')}. These skills are mentioned in this sample but are not evidenced in your supplied skills.</p>}</div></section>
      <div className="sectionHeading"><div><span className="kicker">Your opportunities · {level}</span><h3>Roles to consider, with reasons</h3></div><span>{roles.length} adverts</span></div>
      {roles.length?<div className="fitListings">{roles.map(job=><FitCard key={job.id} job={job}/>)}</div>:<div className="dataEmpty"><BriefcaseBusiness size={24}/><b>No adverts at this level in the collected sample</b><p>Try another level or location. This does not establish that there are no jobs in the wider market.</p></div>}
    </>:<div className="dataEmpty"><BriefcaseBusiness size={30}/><b>{collecting?'The market view will appear when the collection completes':'Market evidence is not available yet'}</b><p>Seniority counts, hiring employers, advertised pay and personal matches will come from the collected job descriptions.</p></div>}
    <SourceFooter source={jobs}/>
  </div>
}
