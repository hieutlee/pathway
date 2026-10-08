import React, {useEffect, useMemo, useState, useRef} from 'react'
import {createRoot} from 'react-dom/client'
import {AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar} from 'recharts'
import {UploadCloud, Sparkles, Compass, BriefcaseBusiness, MapPinned, BadgeCheck, RefreshCw, Clock3, Database, ChevronRight, FileText, CircleCheck, AlertTriangle, Search, Building2, TrendingUp, ShieldCheck, ArrowUpRight, Zap, Users, Target, LoaderCircle, ExternalLink, X, Check, Crown} from 'lucide-react'
import './styles.css'
import Home from './Overview'
import Jobs from './Jobs'
import Migration from './Migration'
import {ProfileSheet, SourcesSheet} from './Profile'
import {Landing, ResumeReview, SAMPLE_RESUME} from './ResumeReview'

const API = '/api'

const defaultProfile = {
  name: 'Your profile', location: 'Brisbane, QLD', visa: 'Student visa (subclass 500)', detectedVisa: 'Student visa (subclass 500)', visaExpiry: '2027-02-28',
  occupation: 'Mechatronics Engineer', careerFamily: 'Mechatronics and automation', anzsco: '233999', osca: '',
  roleCandidates: [{title:'Mechatronics Engineer'},{title:'Automation Engineer'},{title:'Controls Engineer'},{title:'Robotics Engineer'}],
  education: 'Bachelor of Engineering', experienceYears: 1, skills: ['Embedded systems','C++','Python','Control systems','CAD'],
  goal: 'Build an engineering career and understand realistic skilled migration options'
}

const emptyCircumstances = {
  dob:'', passport:'', qualification:'', auQualification:null, institution:'', studyState:'', studyRegional:'no', courseCompletion:'', australianStudy:null, specialistEducation:false,
  englishLevel:'', englishTestDate:'', skillsAssessment:'', skillsAssessmentDate:'', auExperienceYears:0, overseasExperienceYears:0, employedInOccupation:'',
  stateEmploymentMonths:0, regionalEmploymentMonths:0, professionalYear:false, naati:false, partner:'', partnerRelationship:'', relationshipMonths:0,
  regional:'', preferredStates:[], employer:'', salary:null, sponsorMonths:0, currentVisaGrantDate:'', targetPoints:null, fieldOfStudy:''
}
const sampleCircumstances = {...emptyCircumstances, dob:'2001-05-14', passport:'Vietnam', fieldOfStudy:'engineering', qualification:'bachelor', auQualification:true, institution:'QUT', studyState:'QLD',
  courseCompletion:'2026-11-20', englishLevel:'proficient', skillsAssessment:'none', partner:'single', regional:'maybe', employer:'', employedInOccupation:'no', preferredStates:['QLD']}

const STORE_KEY='pathway.state.v3'
function loadSaved(){try{const raw=localStorage.getItem(STORE_KEY);return raw?JSON.parse(raw):null}catch(e){return null}}
function save(state){try{localStorage.setItem(STORE_KEY,JSON.stringify(state))}catch(e){}}

function resumeEvidence(r){
  if(!r) return []
  const out=[],add=(source,text)=>{if(text&&text.trim()) out.push({source:source.slice(0,150),text:text.slice(0,2400)})}
  ;(r.experience||[]).filter(e=>e.included!==false).forEach(e=>add(`Work · ${e.title||'Role'}${e.org?` at ${e.org}`:''}`,`${e.title||''}. ${(e.bullets||[]).join(' ')}`))
  ;(r.projects||[]).forEach(p=>add(`Project · ${p.name}`,`${(p.tools||[]).join(', ')}. ${(p.bullets||[]).join(' ')}`))
  ;(r.volunteering||[]).forEach(v=>add(`Volunteering · ${v.title||v.org}`,`${v.title||''}. ${(v.bullets||[]).join(' ')}`))
  ;(r.education||[]).filter(e=>e.level!=='secondary').forEach(e=>add(`Degree · ${e.degree}`,`${e.degree} ${e.major||''}. ${(e.notes||e.achievements||[]).join(' ')}`))
  ;(r.publications||[]).forEach(p=>add('Publication',p))
  if(r.summary) add('Your summary',r.summary)
  ;(r.certifications||[]).forEach(c=>add(`Certification · ${c.issuer||c.name}`,c.name))
  ;(r.skillGroups||[]).forEach(g=>add(`Skills · ${g.name}`,`${g.name}: ${(g.items||[]).join(', ')}`))
  return out.slice(0,80)
}

function jobsSummary(jobs){
  if(!jobs||typeof jobs.count!=='number') return null
  const wr=jobs.market?.all?.workRights?.counts||{}
  return {count:jobs.count,role:jobs.query?.role,location:jobs.query?.location,collectedAt:jobs.collectedAt,sponsorship:wr.sponsorship||0,noSponsorship:wr.no_sponsorship||0,citizenOrPr:wr.citizen_pr||0,clearance:wr.clearance||0,workRights:wr.work_rights||0}
}

const initialSources = [
  {id:'migration', label:'SkillSelect invitation data', detail:'Department of Home Affairs', status:'idle'},
  {id:'occupation', label:'Occupation and shortage intelligence', detail:'Jobs and Skills Australia', status:'idle'},
  {id:'vacancies', label:'Australian vacancy demand', detail:'JSA Internet Vacancy Index', status:'idle'},
  {id:'jobs', label:'Relevant open roles', detail:'Apify job listings', status:'idle'}
]

function App(){
  const saved=useMemo(loadSaved,[])
  const [screen,setScreen]=useState('onboarding')
  const [profile,setProfile]=useState(saved?.profile||defaultProfile)
  const [circumstances,setCircumstances]=useState(saved?.circumstances||sampleCircumstances)
  const [isSample,setIsSample]=useState(saved?saved.isSample!==false:true)
  const [activeStrategy,setActiveStrategy]=useState(saved?.activeStrategy||null)
  const [checks,setChecks]=useState(saved?.checks||{})
  const [plan,setPlan]=useState(null)
  const [planLoading,setPlanLoading]=useState(false)
  const [planError,setPlanError]=useState('')
  const [planNonce,setPlanNonce]=useState(0)
  const [resume,setResume]=useState(saved?.resume||null)
  const [catalogue,setCatalogue]=useState([])
  useEffect(()=>{fetch(`${API}/occupations`).then(r=>r.ok?r.json():null).then(d=>d&&setCatalogue(d.occupations||[])).catch(()=>{})},[])
  const [sources,setSources]=useState(initialSources)
  const [data,setData]=useState(null)
  const [busy,setBusy]=useState(false)
  const [fileName,setFileName]=useState('')
  const [error,setError]=useState('')
  const [activeTab,setActiveTab]=useState('Home')
  const [profileOpen,setProfileOpen]=useState(false)
  const [sourcesOpen,setSourcesOpen]=useState(false)
  const jobSequence=useRef(0)
  const updateCircumstances=v=>{setIsSample(false);setCircumstances(v)}

  useEffect(()=>{save({profile,circumstances,activeStrategy,checks,fileName,isSample,resume})},[profile,circumstances,activeStrategy,checks,fileName,isSample,resume])
  const jobSignal=useMemo(()=>jobsSummary(data?.jobs),[data?.jobs])
  const jobSignalKey=JSON.stringify(jobSignal)
  useEffect(()=>{
    if(screen!=='dashboard') return
    const controller=new AbortController()
    setPlanLoading(true)
    const timer=setTimeout(async()=>{
      try{
        const res=await fetch(`${API}/migration/plan`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile,circumstances,jobs:jobSignal}),signal:controller.signal})
        if(!res.ok) throw new Error(`Plan failed: ${res.status}`)
        const next=await res.json()
        if(!controller.signal.aborted){setPlan(next);setPlanError('')}
      }catch(e){if(!controller.signal.aborted) setPlanError('The migration planner could not be reached. Your answers are saved; retry when the backend is running.')}
      finally{if(!controller.signal.aborted) setPlanLoading(false)}
    },450)
    return ()=>{clearTimeout(timer);controller.abort()}
  },[screen,profile,circumstances,jobSignalKey,planNonce])
  function toggleCheck(id){setChecks(prev=>{const next={...prev};if(next[id]) delete next[id]; else next[id]=new Date().toISOString();return next})}
  function onJobsAction(action){setActiveTab('Jobs');searchJobs({role:action.role||profile.occupation,location:action.location||profile.location,dateWindow:'pastWeek'})}

  function acceptJobs(payload){
    setData(prev=>({...prev,jobs:payload}))
    setSources(prev=>prev.map(s=>s.id==='jobs'?{...s,status:payload.status,cached:payload.cached,checkedAt:payload.checkedAt,freshness:payload.freshness}:s))
  }
  function jobBody(query,startIfMissing,p=profile){
    return {...query,startIfMissing,profile:{occupation:query.role||p.occupation||'',skills:(p.skills||[]).slice(0,150),experienceYears:p.experienceYears===''||p.experienceYears==null?null:Number(p.experienceYears),visa:p.visa||'',evidence:resumeEvidence(p.resume)}}
  }
  async function fetchJobs(query,startIfMissing=true,signal){
    const res=await fetch(`${API}/jobs/search`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(jobBody(query,startIfMissing)),signal:signal||AbortSignal.timeout(90000)})
    if(!res.ok) throw new Error(`Job search failed: ${res.status}`)
    return res.json()
  }
  async function searchJobs(query){
    const sequence=++jobSequence.current
    acceptJobs({status:'loading',collectionState:'starting',query,count:null,roles:[],note:'Checking cached adverts for this search.'})
    try{
      const payload=await fetchJobs(query)
      if(sequence===jobSequence.current) acceptJobs(payload)
    }catch(e){if(sequence===jobSequence.current) acceptJobs({status:'unavailable',query,count:null,roles:[],note:'The search could not be checked. Search again to check its persisted status.'})}
  }
  useEffect(()=>{
    const jobs=data?.jobs
    if(!jobs?.queryId||!jobs.pollAfterSeconds||screen!=='dashboard') return
    const controller=new AbortController(), sequence=jobSequence.current
    const timer=setTimeout(async()=>{
      try{
        const payload=await fetchJobs(jobs.query,Boolean(jobs.pollStartIfMissing),controller.signal)
        if(!controller.signal.aborted&&sequence===jobSequence.current) acceptJobs(payload)
      }catch(e){
        if(!controller.signal.aborted&&sequence===jobSequence.current) acceptJobs({...jobs,pollAfterSeconds:null,collectionNote:'Collection status could not be checked. Use Explore role to resume checking the same run.'})
      }
    },jobs.pollAfterSeconds*1000)
    return ()=>{clearTimeout(timer);controller.abort()}
  },[data?.jobs,screen])

  async function parseResume(file){
    setBusy(true); setError(''); setFileName(file.name)
    try{
      const body=new FormData(); body.append('file',file)
      const res=await fetch(`${API}/profile/parse-resume`,{method:'POST',body})
      if(!res.ok) throw new Error('Resume analysis failed')
      const parsed=await res.json()
      if(parsed.status!=='parsed'||!parsed.resume){setError(parsed.note||'This file could not be read. Try a text-based PDF or DOCX.');return}
      const {found,englishNote,studyRegionalNote,visa:_v,...hints}=parsed.migrationHints||{}
      setResume(parsed.resume)
      setProfile({...defaultProfile,name:parsed.resume.name||'',location:parsed.resume.location||'',visa:parsed.visa||'',detectedVisa:parsed.visa||'',visaExpiry:'',occupation:'',anzsco:'',roleCandidates:[],skills:[],goal:''})
      setCircumstances({...emptyCircumstances,englishLevel:hints.englishLevel||'',naati:!!hints.naati,professionalYear:!!hints.professionalYear})
      setIsSample(false); setChecks({}); setActiveStrategy(null); setPlan(null)
      setScreen('review')
    }catch(e){
      setError('The resume reader could not be reached. Check the backend is running, or explore the sample profile.')
    }finally{setBusy(false)}
  }
  function confirmReview(patch,circ){
    const next={...profile,...patch}
    setProfile(next); setCircumstances(prev=>({...prev,...circ})); setResume(patch.resume)
    runIntelligence(next)
  }

  async function runIntelligence(p=profile){
    ++jobSequence.current; setScreen('dashboard'); setBusy(true); setData(null); setSources(initialSources.map(s=>({...s,status:s.id==='jobs'?'idle':'loading'})))
    // Jobs are searched on demand from the Jobs tab, so the desired role is never assumed.
    const order=['migration','occupation','vacancies']
    try{
      const tasks=order.map(async (key,i)=>{
        setSources(prev=>prev.map(s=>s.id===key?{...s,status:'loading'}:s))
        const params=new URLSearchParams({
          occupation: p.occupation||'',
          state: (p.location||'').split(',').pop()?.trim()||'QLD',
          anzsco: p.anzsco||'',
          ...(key==='occupation'?{osca:p.osca||''}:{})
        })
        if(key==='migration'){
          params.set('visa',p.visa||'')
          params.set('experienceYears',String(p.experienceYears||0))
          params.set('education',p.education||'')
        }
        let payload
        try{
          const res=key==='jobs'?await fetch(`${API}/jobs/search`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(jobBody({role:p.occupation,location:p.location,dateWindow:'anyTime'},true,p)),signal:AbortSignal.timeout(90000)}):await fetch(`${API}/intelligence/${key}?${params.toString()}`,{signal:AbortSignal.timeout(90000)})
          if(!res.ok) throw new Error(`Request failed: ${res.status}`)
          payload=await res.json()
        }catch(error){
          payload={status:'unavailable',note:'This source did not return usable data. Try refreshing.',freshness:'Request failed'}
        }
        setSources(prev=>prev.map(s=>s.id===key?{...s,status:payload.status||'unavailable',cached:payload.cached,checkedAt:payload.checkedAt,freshness:payload.freshness}:s))
        setData(prev=>({...((prev&&typeof prev==='object')?prev:{}),[key]:payload}))
        return [key,payload]
      })
      const entries=await Promise.all(tasks)
      const intelligence=Object.fromEntries(entries)
      const rec=await fetch(`${API}/recommend`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile:p,intelligence})}).then(r=>r.json())
      setData(prev=>({...prev,recommendation:rec}))
    }catch(e){setError('Some live sources could not be reached. Pathway has kept source failures visible rather than disguising them as fresh data.')}
    finally{setBusy(false)}
  }

  const migration={openProfile:()=>setProfileOpen(true),plan,loading:planLoading,error:planError,circumstances,setCircumstances:updateCircumstances,activeId:activeStrategy,setActiveId:setActiveStrategy,checks,toggleCheck,onJobsAction,onRefresh:()=>setPlanNonce(n=>n+1),sample:isSample,setProfile}
  if(screen==='onboarding') return <Landing busy={busy} error={error} fileName={fileName} onFile={parseResume} onDemo={()=>{setResume(SAMPLE_RESUME);setFileName('');setProfile(defaultProfile);setCircumstances(sampleCircumstances);setIsSample(true);setChecks({});setActiveStrategy(null);setScreen('review')}} saved={saved} onResume={()=>runIntelligence()}/>
  const startOver=()=>{setProfileOpen(false);setError('');setScreen('onboarding')}
  const editResume=()=>{setProfileOpen(false);setScreen('review')}
  const sheets=<><ProfileSheet catalogue={catalogue} open={profileOpen} onClose={()=>setProfileOpen(false)} profile={profile} setProfile={setProfile} c={circumstances} set={updateCircumstances} plan={plan} onEditResume={editResume} onStartOver={startOver}/><SourcesSheet open={sourcesOpen} onClose={()=>setSourcesOpen(false)} sources={sources} busy={busy} onRefresh={()=>{setSourcesOpen(false);runIntelligence()}} renderBadge={s=><StatusBadge source={s}/>} renderInsight={s=><SourceInsight id={s.id} data={data} loading={s.status==='loading'}/>}/></>
  if(screen==='review') return <ResumeReview key={resume?.name+fileName} initialResume={resume||SAMPLE_RESUME} profile={profile} fileName={fileName} catalogue={catalogue} onBack={()=>{setError('');setScreen('onboarding')}} onConfirm={confirmReview}/>
  return <><Dashboard profile={profile} data={data} sources={sources} busy={busy} error={error} activeTab={activeTab} setActiveTab={setActiveTab} refresh={()=>runIntelligence()} openProfile={()=>setProfileOpen(true)} openSources={()=>setSourcesOpen(true)} onJobSearch={searchJobs} migration={migration}/>{sheets}</>
}

function Brand(){return <div className="brand"><div className="brandmark"><Compass size={20}/></div><span>Pathway</span><span className="beta">LIVE</span></div>}

function StatusBadge({source}){
  const labels={loading:'Loading',idle:'Waiting',fresh:source.cached?'Verified · cached':'Verified',partial:'Incomplete data',unavailable:'Unavailable',not_configured:'Not connected',stale:'Older data'}
  const good=source.status==='fresh',loading=source.status==='loading'
  return <span className={`status ${good?'fresh':loading?'loading':'bad'}`}>{loading?<LoaderCircle className="spin"/>:good?<CircleCheck/>:<AlertTriangle/>}{labels[source.status]||'Unknown status'}</span>
}

const TABS=[{id:'Home',icon:Compass},{id:'Jobs',icon:BriefcaseBusiness},{id:'Visa',icon:MapPinned}]
function SourcesButton({sources,onClick}){
  const live=sources.filter(s=>s.status==='fresh').length,loading=sources.some(s=>s.status==='loading')
  return <button className={`srcBtn ${loading?'loading':live===sources.length?'ok':'partial'}`} onClick={onClick} title="Data sources">{loading?<LoaderCircle size={14} className="spin"/>:<i/>}{loading?'Checking sources':`${live} of ${sources.length} sources live`}</button>
}
function Dashboard({profile,data,sources,busy,error,activeTab,setActiveTab,refresh,openProfile,openSources,onJobSearch,migration}){
  const hour=new Date().getHours()
  const first=(profile.name||'').split(' ')[0]
  return <div className="appShell">
    <aside><Brand/><button className="userCard" onClick={openProfile} aria-label="Open your profile"><div className="avatar">{profile.name?.charAt(0)||'P'}</div><div><b>Your profile</b><span>{profile.occupationTitle||profile.occupation}</span></div><ChevronRight size={15}/></button><div className="sideNav">{TABS.map(t=><button key={t.id} className={activeTab===t.id?'active':''} onClick={()=>setActiveTab(t.id)}><t.icon/>{t.id}{t.id==='Visa'&&(migration.plan?.deadlines||[]).some(d=>d.severity==='high'&&d.daysAway<=90)&&<em className="navBadge"/>}</button>)}</div></aside>
    <main className="dashboard">
      <header><div><h1>{`Good ${hour<12?'morning':hour<18?'afternoon':'evening'}${first?`, ${first}`:''}.`}</h1><p>{activeTab==='Home'?'What to do next, in one place.':activeTab==='Jobs'?'Real adverts compared with your profile.':'Your routes to permanent residence, step by step.'}</p></div><div className="headerActions"><SourcesButton sources={sources} onClick={openSources}/><button className="refresh" onClick={refresh} disabled={busy}><RefreshCw className={busy?'spin':''}/> Refresh</button><button className="mobileAvatar" onClick={openProfile} aria-label="Open your profile">{profile.name?.charAt(0)||'P'}</button></div></header>
      <nav className="mobileTabs" aria-label="Sections">{TABS.map(t=><button key={t.id} className={activeTab===t.id?'on':''} onClick={()=>setActiveTab(t.id)}>{t.id}</button>)}</nav>
      {error&&<div className="warning wide"><AlertTriangle/>{error}</div>}
      <CandidateView data={data} busy={busy} profile={profile} activeTab={activeTab} setActiveTab={setActiveTab} onJobSearch={onJobSearch} migration={migration}/>
    </main>
  </div>
}

function SourceInsight({id,data,loading}){
  if(loading && !data?.[id]) return <div className="sourceInsight loadingInsight"><LoaderCircle className="spin"/><span>Retrieving source data…</span></div>
  const d=data?.[id]
  if(!d) return <div className="sourceInsight"><strong>Waiting for analysis</strong></div>
  let title='Data unavailable',detail=d.note||d.shortageNote||'No verified result was returned.'
  if(id==='migration'&&d.latestRound?.date){title=d.latestRound.date;detail=`${d.latestRound.invitations?.toLocaleString()} invitations · ${d.latestRound.scoreForOccupation||'No occupation score matched'}`}
  if(id==='occupation'&&d.occupationResult){title=d.occupationResult.stateRating||d.occupationResult.nationalRating||'Rating unavailable';detail=`${d.oslYear} OSL · ${d.occupationResult.state} · ${d.occupationResult.occupation}`}
  if(id==='vacancies'){title=d.releasePeriod||'Release unavailable';detail=d.releaseDate?`Released ${d.releaseDate} · national IVI publication`:d.note||d.subheadline||'Release metadata could not be extracted.'}
  if(id==='jobs'){title=typeof d.count==='number'?`${d.count} matching listings`:d.status==='not_configured'?'Not connected':d.status==='loading'?'Collecting adverts':'Results unavailable';detail=d.note}
  return <div className="sourceInsight"><strong>{title}</strong><span>{detail}</span></div>
}

function Skeleton({height=120}){return <div className="skeleton" style={{height}}><div></div><div></div><div></div></div>}
const SourceNote=({source})=><div className="sourceNote"><Clock3/> {source?.source||'Source pending'} <span>{source?.freshness||'checking'}</span></div>

function CandidateView({data,busy,profile,activeTab,setActiveTab,onJobSearch,migration}){
  if(activeTab==='Visa') return <Migration {...migration} profile={profile} jobs={data?.jobs}/>
  if(activeTab==='Jobs') return data?<Jobs jobs={data.jobs} profile={profile} onSearch={onJobSearch} disabled={busy} demand={data.occupation}/>:<div className="cardsGrid"><Skeleton height={230}/><Skeleton height={230}/><Skeleton height={230}/></div>
  return <Home data={data||{}} profile={profile} plan={migration.plan} planLoading={migration.loading} activeId={migration.activeId} checks={migration.checks} toggleCheck={migration.toggleCheck} setActiveTab={setActiveTab} onJobsAction={migration.onJobsAction} openProfile={migration.openProfile}/>
}

createRoot(document.getElementById('root')).render(<App/>)
