import React from 'react'
import {Target, BriefcaseBusiness, TrendingUp, MapPinned, ExternalLink, CircleCheck, AlertTriangle, ChevronRight, Clock3, Compass, FileText} from 'lucide-react'

export function dateLabel(value, withTime=false){
  if(!value) return 'Not recorded'
  const date=new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('en-AU', {day:'numeric',month:'short',year:'numeric',...(withTime?{hour:'2-digit',minute:'2-digit'}:{})})
}

export function SourceLink({source,children}){
  if(!source?.sourceUrl) return null
  return <a className="evidenceLink" href={source.sourceUrl} target="_blank" rel="noreferrer">{children||source.source||'Official source'}<ExternalLink size={12}/></a>
}

export function SourceFooter({source}){
  if(!source) return <p className="evidenceFoot">Waiting for source data</p>
  return <div className="evidenceFoot"><SourceLink source={source}/>{source.checkedAt&&<span>Retrieved {dateLabel(source.checkedAt,true)}{source.cached?' · cached response':''}</span>}</div>
}

function OverviewMetric({icon,label,value,detail,source,strong=false}){
  return <section className={`overviewMetric ${strong?'accentMetric':''}`}><div className="overviewMetricLabel">{icon}<span>{label}</span></div><strong>{value}</strong><p>{detail}</p>{source&&<SourceLink source={source}>View source</SourceLink>}</section>
}

export function JobResults({jobs,limit=4}){
  const roles=jobs?.roles||[]
  if(!roles.length){
    const title=!jobs?'No job search yet':jobs.status==='loading'?'Collecting adverts':jobs.status==='not_configured'?'Connect a job source':jobs.count===0?'No matches in this collection':'Vacancy results unavailable'
    return <div className="dataEmpty"><BriefcaseBusiness size={26}/><b>{title}</b><p>{jobs?.note||'Open Jobs and search a role. Adverts are compared with your resume and ranked by whether you can apply.'}</p></div>
  }
  return <><div className="listingGrid">{roles.slice(0,limit).map((job,index)=><article className="realListing" key={job.url||index}>
    <div className="listingHeading"><div className="jobLogo">{job.company?.charAt(0)||'J'}</div><div><a href={job.url} target="_blank" rel="noreferrer">{job.title}<ExternalLink size={13}/></a><span>{job.company||'Employer not listed'} · {job.location}</span></div></div>
    <p className="listingReason">{job.reason}</p>
    {job.salary&&<span className="listingSalary">{job.salary}</span>}
    <small>{job.postedAt?`Advert date: ${dateLabel(job.postedAt)}`:'Advert date not supplied'}</small>
  </article>)}</div><p className="collectionNote">{jobs.note}</p></>
}

export default function Overview({data,profile,setActiveTab,onUpgrade,migrationCard=null}){
  const rec=data.recommendation||{}, completeness=rec.profileCompleteness
  const migration=data.migration, round=migration?.latestRound||{}, shortage=data.occupation, occupation=shortage?.occupationResult, jobs=data.jobs
  const jobValue=typeof jobs?.count==='number'?jobs.count.toLocaleString():jobs?.status==='not_configured'?'Not connected':jobs?.status==='loading'?'Collecting':jobs?'Unavailable':'Not searched yet'
  const shortageValue=occupation?.stateRating||occupation?.nationalRating||(shortage?.status==='unavailable'?'Unavailable':shortage?'Not matched':'Loading')
  return <div className="overviewContent">
    <div className="overviewMetrics">
      <OverviewMetric icon={<Target size={18}/>} label="Profile details" value={completeness?`${completeness.completed} of ${completeness.total}`:'Checking'} detail="Fields supplied. Review the checklist below." strong/>
      <OverviewMetric icon={<BriefcaseBusiness size={18}/>} label="Collected job adverts" value={jobValue} detail={typeof jobs?.count==='number'?`From ${jobs.scannedCount} retrieved rows for ${jobs.query?.location||profile.location}.`:(jobs?'A connected provider is needed to count vacancies.':'Search a role in Jobs to collect adverts and compare them with your resume.')} source={jobs}/>
      <OverviewMetric icon={<TrendingUp size={18}/>} label={occupation?.stateRating?`${occupation.state} shortage rating`:'National shortage rating'} value={shortageValue} detail={occupation?`${shortage.oslYear} OSL · ${occupation.occupation}`:shortage?.shortageNote||'Reading the published occupation workbook.'} source={shortage}/>
      <OverviewMetric icon={<MapPinned size={18}/>} label="Latest published 189 round" value={round.minimumPoints!=null?`${round.minimumPoints} points`:round.invitations!=null?round.invitations.toLocaleString()+' invitations':migration?'Unavailable':'Loading'} detail={round.date?`${round.date} · ${round.minimumPoints!=null?'occupation minimum':'all invited occupations'}`:migration?.note||'Reading Home Affairs invitation tables.'} source={migration}/>
    </div>

    <div className="overviewGrid">
      <section className="card priority overviewPriority"><span className="kicker">Your next action</span><h2>{rec.topAction?.title||'Preparing your next steps'}</h2><p>{rec.topAction?.why||'Recommendations will use your profile and the results returned by each source.'}</p><div className="actionRow"><button className="primary" onClick={onUpgrade}>Build Evidence Plan<ChevronRight size={16}/></button><span><Clock3 size={14}/>{rec.topAction?.time||'After source checks'}</span></div></section>

      {migrationCard}
      <section className="card profileEvidence"><div className="cardHead"><div><span className="kicker">What we know about you</span><h2>Profile checklist</h2></div><FileText/></div><p className="evidenceExplanation">{completeness?.explanation||'Checking which details you supplied.'}</p><div className="profileChecks">{completeness?.checks.map(check=><div key={check.id} className={check.present?'present':'missing'}>{check.present?<CircleCheck size={15}/>:<AlertTriangle size={15}/>}<span>{check.label}</span><b>{check.present?'Supplied':'Needed'}</b></div>)}</div></section>

      <section className="card officialEvidence"><div className="cardHead"><div><span className="kicker">Department of Home Affairs</span><h2>Invitation evidence</h2></div><MapPinned/></div>
        {round.date?<><dl className="evidenceFacts"><div><dt>Published round</dt><dd>{round.date}</dd></div><div><dt>Total subclass 189 invitations</dt><dd>{round.invitations?.toLocaleString()??'Not extracted'}</dd></div><div><dt>Occupation minimum</dt><dd>{round.minimumPoints!=null?`${round.minimumPoints} points`:round.occupationStatus==='unparsed'?'Table unavailable':'No published match'}</dd></div>{round.matchedOccupation&&<div><dt>Official occupation</dt><dd>{round.matchedOccupation}</dd></div>}{migration.occupationMapping&&<div><dt>Selected classification</dt><dd>{migration.occupationMapping.classification} {migration.occupationMapping.code}</dd></div>}{round.tieBreak&&<div><dt>Round tie break date</dt><dd>{round.tieBreak}</dd></div>}</dl><p className="evidenceExplanation">{migration.occupationNote}</p>{migration.mappingNote&&<p className="evidenceCaution">{migration.mappingNote}</p>}</>:<div className="dataEmpty"><AlertTriangle/><b>Round data unavailable</b><p>{migration?.note||'Waiting for the official source.'}</p></div>}
        <SourceFooter source={migration}/>
      </section>

      <section className="card officialEvidence"><div className="cardHead"><div><span className="kicker">Jobs and Skills Australia</span><h2>Occupation shortage</h2></div><TrendingUp/></div>
        {occupation?<><p className="officialOccupation">{occupation.occupation}<span>{occupation.classification} {occupation.code} · {shortage.oslYear} Occupation Shortage List</span></p><dl className="evidenceFacts"><div><dt>Australia</dt><dd>{occupation.nationalRating||'Not assessed'}</dd></div><div><dt>{occupation.state}</dt><dd>{occupation.stateRating||'Rating unavailable'}</dd></div></dl><p className="evidenceExplanation">A shortage describes employer recruitment difficulty. It does not establish your visa eligibility or guarantee a job.</p><details className="ratingDetails"><summary>View all state and territory ratings</summary><dl className="evidenceFacts">{Object.entries(occupation.stateRatings||{}).map(([state,value])=><div key={state}><dt>{state}</dt><dd>{value||'Not assessed'}</dd></div>)}</dl></details><p className="evidenceCaution">{shortage.shortageNote}</p></>:<div className="dataEmpty"><AlertTriangle/><b>{shortage?.status==='unavailable'?'Shortage data unavailable':'Occupation match needed'}</b><p>{shortage?.shortageNote||'Reading the official workbook.'}</p></div>}
        {shortage?.downloadUrl&&<a className="evidenceLink" href={shortage.downloadUrl} target="_blank" rel="noreferrer">Download published workbook<ExternalLink size={12}/></a>}<SourceFooter source={shortage}/>
      </section>

      <section className="card overviewJobs"><div className="cardHead"><div><span className="kicker">Opportunity radar</span><h2>Advertised roles matching your profile</h2></div>{(jobs?.roles?.length||0)>4&&<button className="textBtn" onClick={()=>setActiveTab('Jobs')}>View all<ChevronRight size={15}/></button>}</div>
        {jobs?.collectedAt&&<p className="collectionNote">Collected {dateLabel(jobs.collectedAt,true)}{jobs.status==='stale'?' · This collection needs a refresh.':''}</p>}
        {jobs?.roles?.length>0&&jobs.status==='partial'&&<p className="evidenceCaution">The collection time is unknown. Listing availability has not been verified.</p>}
        <JobResults jobs={jobs}/><SourceFooter source={jobs}/>
      </section>

      <section className="card overviewPathway"><div className="cardHead"><div><span className="kicker">Suggested sequence</span><h2>Your pathway map</h2></div><Compass/></div><p className="evidenceExplanation">Suggested from the information supplied. Completion of these steps has not been independently verified.</p><div className="timeline">{(rec.pathway||[]).slice(0,4).map((step,i)=><div key={i} className={step.status==='current'?'now':step.status==='complete'?'complete':''}><span>{step.status==='complete'?'INPUTS':step.status==='current'?'NOW':String(i+1).padStart(2,'0')}</span><div><b>{step.title}</b><p>{step.detail}</p></div><small>{step.horizon}</small></div>)}</div><button className="textBtn" onClick={()=>setActiveTab('My pathway')}>Open full pathway<ChevronRight size={14}/></button></section>
      <section className="card overviewBlockers"><div className="cardHead"><div><span className="kicker">Details to resolve</span><h2>Current blockers</h2></div><AlertTriangle/></div>{(rec.blockers||[]).slice(0,3).map((blocker,i)=><div className="blocker" key={blocker.code||i}><span>{i+1}</span><div><b>{blocker.title}</b><p>{blocker.detail}</p></div></div>)}</section>
    </div>
  </div>
}
