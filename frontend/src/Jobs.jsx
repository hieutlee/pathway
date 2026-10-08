import React, {useEffect, useMemo, useRef, useState} from 'react'
import {ResponsiveContainer, PieChart, Pie, Cell, Sector} from 'recharts'
import {Search, BriefcaseBusiness, ArrowUpRight, ExternalLink, LoaderCircle, Clock3, Check, MapPin, Sparkles, ShieldAlert, ShieldCheck, CircleAlert, ChevronDown, ChevronUp, Repeat2, Wallet, Info} from 'lucide-react'
import {dateLabel, SourceFooter} from './Overview'
import './jobs.css'

/* ---------- locations (Australia only, so no country suffix) ---------- */
const STATE_NAMES={QLD:'Queensland',NSW:'New South Wales',VIC:'Victoria',SA:'South Australia',WA:'Western Australia',TAS:'Tasmania',ACT:'Australian Capital Territory',NT:'Northern Territory'}
const PLACES=[['Brisbane','QLD'],['Gold Coast','QLD'],['Sunshine Coast','QLD'],['Toowoomba','QLD'],['Townsville','QLD'],['Cairns','QLD'],['Mackay','QLD'],['Rockhampton','QLD'],['Bundaberg','QLD'],['Gladstone','QLD'],['Ipswich','QLD'],['Logan','QLD'],
  ['Sydney','NSW'],['Newcastle','NSW'],['Wollongong','NSW'],['Parramatta','NSW'],['Central Coast','NSW'],['Wagga Wagga','NSW'],['Albury','NSW'],['Orange','NSW'],['Dubbo','NSW'],['Tamworth','NSW'],
  ['Melbourne','VIC'],['Geelong','VIC'],['Ballarat','VIC'],['Bendigo','VIC'],['Shepparton','VIC'],['Mildura','VIC'],
  ['Adelaide','SA'],['Mount Gambier','SA'],['Whyalla','SA'],['Perth','WA'],['Bunbury','WA'],['Geraldton','WA'],['Kalgoorlie','WA'],['Karratha','WA'],['Port Hedland','WA'],
  ['Hobart','TAS'],['Launceston','TAS'],['Devonport','TAS'],['Burnie','TAS'],['Canberra','ACT'],['Darwin','NT'],['Alice Springs','NT']]
const LOCATIONS=[...PLACES.map(([c,s])=>`${c}, ${STATE_NAMES[s]}`),...Object.values(STATE_NAMES),'Australia']
export function prettyLocation(v){
  if(!v) return ''
  const parts=v.split(',').map(x=>x.trim()).filter(x=>x&&x.toLowerCase()!=='australia')
  if(!parts.length) return 'Australia'
  const city=parts[0],st=(parts[1]||'').toUpperCase()
  if(STATE_NAMES[st]) return `${city}, ${STATE_NAMES[st]}`
  if(STATE_NAMES[city.toUpperCase()]) return STATE_NAMES[city.toUpperCase()]
  const known=PLACES.find(([c])=>c.toLowerCase()===city.toLowerCase())
  return known?`${known[0]}, ${STATE_NAMES[known[1]]}`:parts.join(', ')
}
function LocationInput({value,onChange}){
  const [open,setOpen]=useState(false),[hi,setHi]=useState(0)
  const q=value.trim().toLowerCase()
  const matches=q?LOCATIONS.filter(l=>l.toLowerCase().startsWith(q)||l.toLowerCase().split(', ')[0].includes(q)).slice(0,7):LOCATIONS.slice(0,7)
  const pick=l=>{onChange(l);setOpen(false)}
  return <div className="locWrap">
    <MapPin size={16} className="locIcon"/>
    <input value={value} placeholder="City or state" autoComplete="off" role="combobox" aria-expanded={open} aria-autocomplete="list"
      onFocus={()=>setOpen(true)} onBlur={()=>setTimeout(()=>setOpen(false),120)} onChange={e=>{onChange(e.target.value);setOpen(true);setHi(0)}}
      onKeyDown={e=>{if(!open||!matches.length) return;if(e.key==='ArrowDown'){e.preventDefault();setHi(h=>Math.min(matches.length-1,h+1))}else if(e.key==='ArrowUp'){e.preventDefault();setHi(h=>Math.max(0,h-1))}else if(e.key==='Enter'||e.key==='Tab'){if(matches[hi]&&matches[hi]!==value){e.preventDefault();pick(matches[hi])}}else if(e.key==='Escape') setOpen(false)}}/>
    {open&&matches.length>0&&<ul className="locList" role="listbox">{matches.map((l,i)=><li key={l} role="option" aria-selected={i===hi} className={i===hi?'hi':''} onMouseDown={e=>{e.preventDefault();pick(l)}} onMouseEnter={()=>setHi(i)}>{l}</li>)}</ul>}
  </div>
}

/* ---------- small pieces ---------- */
function Tip({text,children,className=''}){return <span className={`tip ${className}`} tabIndex={0}>{children}{text&&<span className="tipBox" role="tooltip">{text}</span>}</span>}
const LEVELS=[['All','All levels'],['Junior','Junior'],['Mid level','Mid-level'],['Senior','Senior']]
const STATUS_LABEL={have:'On your resume',transferable:'Transferable',gap:'Not shown yet'}
const ELIG_CLASS=t=>t===0?'ok':t===1?'check':'no'
const PALETTE=['#0c6b58','#2a9d8f','#6b7fd7','#e4723b','#b0648a','#e9b949','#577590','#8ab17d','#c9d6d0']

function SkillChip({s}){
  const icon=s.status==='have'?<Check size={12}/>:s.status==='transferable'?<Repeat2 size={12}/>:null
  const text=s.status==='gap'?`${s.reason}${s.advertEvidence?` The advert says: “${s.advertEvidence}”`:''}`:`${s.reason}${s.quote?` (“${s.quote}”)`:''}`
  return <Tip text={text} className={`skillChip ${s.status}`}>{icon}{s.skill}</Tip>
}

export function JobCard({job,open,onToggle}){
  const fit=job.fit||{},el=fit.eligibility||{tier:0,label:'No restriction stated'},req=job.experienceRequirement
  const skills=[...(fit.skills||[])].sort((a,b)=>({have:0,transferable:1,gap:2}[a.status]-{have:0,transferable:1,gap:2}[b.status]))
  return <article className={`jobCard tier${el.tier}`}>
    <div className="jcTop">
      <div className="jcLogo">{(job.company||'?').charAt(0)}</div>
      <div className="jcHead"><span className="jcCompany">{job.company||'Employer not named'}</span><h3><a href={job.url} target="_blank" rel="noreferrer">{job.title}<ArrowUpRight size={15}/></a></h3>
        <p>{[prettyLocation(job.location),job.seniority?.level&&job.seniority.level!=='Unspecified'?job.seniority.level.replace('Mid level','Mid-level'):null,job.postedAt?`Posted ${dateLabel(job.postedAt)}`:null].filter(Boolean).join(' · ')}</p></div>
      <div className="jcBadges"><Tip text={`${el.reason}${el.evidence?` Advert: “${el.evidence}”`:''}`} className={`eligBadge ${ELIG_CLASS(el.tier)}`}>{el.tier===0?<ShieldCheck size={13}/>:el.tier===1?<CircleAlert size={13}/>:<ShieldAlert size={13}/>}{el.label}</Tip><span className={`fitBadge ${fit.label?.toLowerCase().replace(' ','')}`}>{fit.label}</span></div>
    </div>
    {skills.length>0&&<div className="jcSkills">{skills.map(s=><SkillChip key={s.skill} s={s}/>)}</div>}
    <div className="jcMeta">
      {req&&<Tip text={req.evidence} className={`metaChip ${fit.experienceGap?'warn':'okm'}`}><Clock3 size={12}/>{req.minimum}+ years asked{fit.experienceGap?` · you have ${Math.max(0,req.minimum-fit.experienceGap).toFixed(1).replace('.0','')}`:' · met'}</Tip>}
      {job.salary&&<span className="metaChip"><Wallet size={12}/>{job.salary.length>60?job.salary.slice(0,58)+'…':job.salary}</span>}
      <span className="jcCount">{fit.haveCount||0} on your resume · {fit.transferableCount||0} transferable · {fit.gapCount||0} to build</span>
    </div>
    <button className="jcMore" onClick={onToggle} aria-expanded={open}>{open?<ChevronUp size={14}/>:<ChevronDown size={14}/>}{open?'Hide reasoning':'Why this ranking'}</button>
    {open&&<div className="jcWhy">
      <p>{(fit.reasons||[]).join(' ')}</p>
      <ul>{skills.map(s=><li key={s.skill} className={s.status}><b>{s.skill}</b><span>{STATUS_LABEL[s.status]}: {s.reason}</span>{s.advertEvidence&&<em>Advert: “{s.advertEvidence}”</em>}</li>)}</ul>
      {el.evidence&&<p className="jcRights"><b>Work rights.</b> {el.reason} <em>“{el.evidence}”</em></p>}
      <a href={job.url} target="_blank" rel="noreferrer">Read the full advert<ExternalLink size={12}/></a>
    </div>}
  </article>
}

/* ---------- market chart ---------- */
function ActiveSlice(props){const {cx,cy,innerRadius,outerRadius,startAngle,endAngle,fill}=props;return <g><Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={outerRadius+8} startAngle={startAngle} endAngle={endAngle} fill={fill}/><Sector cx={cx} cy={cy} innerRadius={outerRadius+11} outerRadius={outerRadius+14} startAngle={startAngle} endAngle={endAngle} fill={fill} opacity={.35}/></g>}
function MarketChart({market,skillStatus,role}){
  const top=market.skills.slice(0,8)
  const restCount=market.skills.slice(8).reduce((n,s)=>n+s.count,0)
  const data=[...top.map((s,i)=>({...s,fill:PALETTE[i]})),...(restCount?[{skill:'Other skills',count:restCount,fill:PALETTE[8],examples:[],other:true}]:[])]
  const totalMentions=data.reduce((n,s)=>n+s.count,0)
  const [active,setActive]=useState(0)
  const sel=data[Math.min(active,data.length-1)]
  const st=sel&&!sel.other?skillStatus?.[sel.skill]:null
  const shown=top.map(s=>skillStatus?.[s.skill]?.status)
  const have=shown.filter(x=>x==='have').length,tr=shown.filter(x=>x==='transferable').length,gap=shown.filter(x=>x==='gap').length
  return <section className="card marketCard">
    <div className="mkHead"><div><span className="kicker">Understand what the market is looking for</span><h3>What employers ask for in {role} adverts</h3><p>From {market.describedCount} adverts with a description. Pick a slice to see what employers wrote and where your resume stands.</p></div>
      <div className="mkScore"><span><b className="g">{have}</b> on your resume</span><span><b className="t">{tr}</b> transferable</span><span><b className="x">{gap}</b> to build</span><small>of the top {top.length} skills</small></div></div>
    <div className="mkBody">
      <div className="mkChart"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} dataKey="count" nameKey="skill" innerRadius="56%" outerRadius="80%" paddingAngle={1.5} activeIndex={active} activeShape={ActiveSlice} onMouseEnter={(_,i)=>setActive(i)} onClick={(_,i)=>setActive(i)} isAnimationActive={false}>{data.map(d=><Cell key={d.skill} fill={d.fill} stroke="#fff" strokeWidth={2}/>)}</Pie></PieChart></ResponsiveContainer>
        <div className="mkCenter"><b>{sel?Math.round(sel.count/market.count*100):0}%</b><span>of adverts mention<br/>{sel?.skill}</span></div></div>
      <div className="mkLegend">{data.map((d,i)=>{const s=skillStatus?.[d.skill];return <button key={d.skill} className={i===active?'on':''} onMouseEnter={()=>setActive(i)} onFocus={()=>setActive(i)} onClick={()=>setActive(i)}><i style={{background:d.fill}}/><span>{d.skill}</span><b>{d.count}</b>{!d.other&&<em className={s?.status||'gap'} title={s?STATUS_LABEL[s.status]:''}/>}</button>})}</div>
      <div className="mkDetail">{sel&&<>
        <h4>{sel.skill}</h4>
        <p className="mkStat">{sel.other?`${sel.count} mentions across less common skills.`:`Mentioned in ${sel.count} of ${market.count} adverts. ${Math.round(sel.count/totalMentions*100)}% of all skill mentions in this sample.`}</p>
        {st&&<div className={`mkYou ${st.status}`}><b>{st.status==='have'?<><Check size={14}/>You have this</>:st.status==='transferable'?<><Repeat2 size={14}/>Transferable from your experience</>:<><Sparkles size={14}/>Worth building</>}</b><p>{st.reason}</p>{st.quote&&<em>“{st.quote}”</em>}</div>}
        {(sel.examples||[]).slice(0,2).map((e,i)=><a key={i} className="mkQuote" href={e.url} target="_blank" rel="noreferrer"><span>“{e.evidence}”</span><small>{e.title}{e.company?` · ${e.company}`:''}<ExternalLink size={11}/></small></a>)}
      </>}</div>
    </div>
    <p className="jobMethod"><Info size={12}/>Each slice is a share of all skill mentions, and one advert can mention several skills. A mention is not always a requirement. The sample covers {market.count} adverts from one search, not the whole market.</p>
  </section>
}

/* ---------- page ---------- */
export default function Jobs({jobs,profile,onSearch,disabled=false,demand=null}){
  const [role,setRole]=useState(jobs?.query?.role||'')
  const [location,setLocation]=useState(prettyLocation(jobs?.query?.location||profile.location||''))
  const [window,setWindow]=useState(jobs?.query?.dateWindow==='past24Hours'?'past24Hours':'pastWeek')
  const [level,setLevel]=useState('All')
  const [submitting,setSubmitting]=useState(false)
  const [openId,setOpenId]=useState(null)
  const [showClosed,setShowClosed]=useState(false)
  useEffect(()=>{if(jobs?.query){setRole(jobs.query.role);setLocation(prettyLocation(jobs.query.location))}setLevel('All')},[jobs?.queryId])
  const available=typeof jobs?.count==='number'&&jobs?.market
  const collecting=['running','starting','checking_cache'].includes(jobs?.collectionState)||jobs?.status==='loading'
  const market=available?(level==='All'?jobs.market.all:jobs.market.byLevel[level]):null
  const roles=(jobs?.roles||[]).filter(j=>level==='All'||j.seniority?.level===level)
  const groups=[0,1,2].map(t=>roles.filter(j=>(j.fit?.eligibility?.tier??0)===t))
  const suggestions=[...new Set((profile.roleCandidates||[]).map(r=>typeof r==='string'?r:r.title).filter(Boolean))].slice(0,5)
  async function search(event,searchRole=role){
    event?.preventDefault()
    if(!searchRole.trim()||!location.trim()) return
    setSubmitting(true);setRole(searchRole)
    try{await onSearch({role:searchRole.trim(),location:location.trim(),dateWindow:window})}finally{setSubmitting(false)}
  }
  const searchedRole=jobs?.query?.role||role
  return <div className="singleView jobsIntelligence jobs2">
    <section className="card searchCard"><form className="searchForm" onSubmit={search}>
      <label className="sfRole"><span>Desired role</span><div className="sfInput"><Search size={16}/><input value={role} onChange={e=>setRole(e.target.value)} minLength={2} maxLength={160} required placeholder={suggestions[0]?`e.g. ${suggestions[0]}`:'e.g. Controls Engineer'}/></div></label>
      <label className="sfLoc"><span>Location</span><LocationInput value={location} onChange={setLocation}/></label>
      <label className="sfDate"><span>Posted</span><select value={window} onChange={e=>setWindow(e.target.value)}><option value="past24Hours">Latest (24 hours)</option><option value="pastWeek">Last week</option></select></label>
      <button type="submit" className="primary" disabled={submitting||disabled||!role.trim()||!location.trim()}>{submitting?<LoaderCircle size={16} className="spin"/>:<Search size={16}/>}Search jobs</button>
    </form>
    {suggestions.length>0&&<div className="sfSuggest"><span><Sparkles size={13}/>Suggested from your resume</span>{suggestions.map(t=><button type="button" key={t} disabled={disabled||submitting} onClick={()=>search(null,t)}>{t}</button>)}</div>}
    </section>

    {(jobs||collecting)&&<div className={`collectionBanner ${jobs?.status==='stale'?'older':''}`} aria-live="polite">{collecting?<LoaderCircle size={17} className="spin"/>:<Clock3 size={17}/>}<div><b>{collecting?'Collecting adverts for this search':available?`${searchedRole} · ${prettyLocation(jobs.query?.location)}`:'No usable collection yet'}</b><p>{jobs?.note||'Searching…'}</p>{jobs?.collectedAt&&<small>Collected {dateLabel(jobs.collectedAt,true)} · {jobs.cached?'Reused collection':'Latest collection'} · within about 40 km</small>}{jobs?.collectionNote&&<p>{jobs.collectionNote}</p>}</div></div>}

    {!jobs&&!collecting&&<section className="card jobsEmpty"><BriefcaseBusiness size={28}/><div><h3>Search a role to see real adverts compared with your resume</h3><p>Pick a suggestion above or type any role. Pathway reads each advert, shows what employers ask for, and ranks the roles you can apply for first.</p></div></section>}

    {available&&<>
      <div className="levelBar" role="tablist">{LEVELS.map(([key,label])=>{const n=key==='All'?jobs.count:jobs.market.all.levels.find(l=>l.level===key)?.count||0;return <button key={key} role="tab" aria-selected={level===key} className={level===key?'on':''} onClick={()=>setLevel(key)}>{label}<b>{n}</b></button>})}</div>
      {market.skills.length>0?<MarketChart market={market} skillStatus={jobs.skillStatus} role={searchedRole}/>:<section className="card"><p className="dataHint">No recognised skills were mentioned in these adverts. Read them directly below.</p></section>}
      <div className="jobsSideGrid">
        <section className="card"><span className="kicker">{market.salaryDisclosedCount} of {market.count} show pay</span><h3>Advertised pay</h3>{market.salaries.length?<div className="salaryGroups">{market.salaries.map((s,i)=><div key={i}><strong>{s.currency} {Number(s.min).toLocaleString('en-AU')}{s.max!==s.min?` to ${Number(s.max).toLocaleString('en-AU')}`:''}<small> / {s.period}</small></strong><span>{s.basis} · {s.count} advert{s.count>1?'s':''}</span></div>)}</div>:<p className="dataHint">No comparable pay in this sample. Missing pay is never treated as zero.</p>}</section>
        {market.workRights&&<section className="card"><span className="kicker">Work rights in this sample</span><h3>Who can apply</h3>{(()=>{const w=market.workRights.counts;const rows=[['Citizens or PR only',w.citizen_pr,'no'],['Security clearance',w.clearance,'no'],['Work rights required',w.work_rights,'ok'],['Sponsorship mentioned',w.sponsorship,'ok'],['No sponsorship',w.no_sponsorship,'check'],['Not stated',w.not_stated,'']].filter(r=>r[1]);return <div className="wrList">{rows.map(([l,n,c])=><div key={l}><i className={c}/><span>{l}</span><b>{n}</b></div>)}</div>})()}</section>}
        <DemandMini demand={demand}/>
      </div>
      <div className="rankHead"><div><span className="kicker">Ranked for you</span><h3>Roles you can apply for first, then the rest</h3></div><div className="legendRow"><span className="skillChip have"><Check size={12}/>On your resume</span><span className="skillChip transferable"><Repeat2 size={12}/>Transferable</span><span className="skillChip gap">Not shown yet</span><span className="eligBadge no"><ShieldAlert size={12}/>Restriction</span></div></div>
      {roles.length===0&&<div className="dataEmpty"><BriefcaseBusiness size={24}/><b>No adverts at this level in the sample</b><p>Try another level. This does not mean there are no such jobs in the wider market.</p></div>}
      {groups[0].length>0&&<><h4 className="groupHead ok"><ShieldCheck size={15}/>You can apply · {groups[0].length}</h4><div className="jobList">{groups[0].map(j=><JobCard key={j.id} job={j} open={openId===j.id} onToggle={()=>setOpenId(openId===j.id?null:j.id)}/>)}</div></>}
      {groups[1].length>0&&<><h4 className="groupHead check"><CircleAlert size={15}/>Check before applying · {groups[1].length}</h4><div className="jobList">{groups[1].map(j=><JobCard key={j.id} job={j} open={openId===j.id} onToggle={()=>setOpenId(openId===j.id?null:j.id)}/>)}</div></>}
      {groups[2].length>0&&<><button className="groupHead no closedToggle" onClick={()=>setShowClosed(!showClosed)}><ShieldAlert size={15}/>Citizens, PR or clearance only · {groups[2].length}{showClosed?<ChevronUp size={15}/>:<ChevronDown size={15}/>}</button>{showClosed&&<div className="jobList">{groups[2].map(j=><JobCard key={j.id} job={j} open={openId===j.id} onToggle={()=>setOpenId(openId===j.id?null:j.id)}/>)}</div>}</>}
    </>}
    {jobs&&<SourceFooter source={jobs}/>}
  </div>
}

function DemandMini({demand}){
  const o=demand?.occupationResult
  return <section className="card"><span className="kicker">Jobs and Skills Australia</span><h3>Shortage rating</h3>{o?<p className="demandLine"><b>{o.occupation}</b>: <b>{o.nationalRating||'not assessed'}</b> nationally{o.state&&o.stateRating?<>, <b>{o.stateRating}</b> in {o.state}</>:''} ({demand.oslYear} list).</p>:<p className="dataHint">{demand?.status==='unavailable'?'The shortage list could not be loaded right now.':'No rating matched your occupation.'}</p>}{demand?.sourceUrl&&<a className="evidenceLink" href={demand.downloadUrl||demand.sourceUrl} target="_blank" rel="noreferrer">Source<ExternalLink size={12}/></a>}</section>
}
