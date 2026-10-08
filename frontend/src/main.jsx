import React, {useEffect, useMemo, useState, useRef} from 'react'
import {createRoot} from 'react-dom/client'
import {AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar} from 'recharts'
import {UploadCloud, Sparkles, Compass, BriefcaseBusiness, MapPinned, BadgeCheck, RefreshCw, Clock3, Database, ChevronRight, FileText, CircleCheck, AlertTriangle, Search, Building2, TrendingUp, ShieldCheck, ArrowUpRight, Zap, Users, Target, LoaderCircle, ExternalLink, X, Check, Crown} from 'lucide-react'
import './styles.css'
import Overview from './Overview'
import Jobs from './Jobs'
import Migration, {MigrationSummaryCard, MigrationMilestones} from './Migration'

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
  regional:'', preferredStates:[], employer:'', salary:null, sponsorMonths:0, currentVisaGrantDate:'', previous485:false, exceptionalTalent:false, targetPoints:null
}
const sampleCircumstances = {...emptyCircumstances, dob:'2001-05-14', passport:'Vietnam', qualification:'bachelor', auQualification:true, institution:'QUT', studyState:'QLD',
  courseCompletion:'2026-11-20', englishLevel:'proficient', skillsAssessment:'none', partner:'single', regional:'maybe', employer:'none', employedInOccupation:'no', preferredStates:['QLD']}

const STORE_KEY='pathway.state.v2'
function loadSaved(){try{const raw=localStorage.getItem(STORE_KEY);return raw?JSON.parse(raw):null}catch(e){return null}}
function save(state){try{localStorage.setItem(STORE_KEY,JSON.stringify(state))}catch(e){}}

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
  const [sources,setSources]=useState(initialSources)
  const [data,setData]=useState(null)
  const [busy,setBusy]=useState(false)
  const [fileName,setFileName]=useState('')
  const [error,setError]=useState('')
  const [activeTab,setActiveTab]=useState('Overview')
  const [employerMode,setEmployerMode]=useState(false)
  const [pricingOpen,setPricingOpen]=useState(false)
  const jobSequence=useRef(0)
  const updateCircumstances=v=>{setIsSample(false);setCircumstances(v)}

  useEffect(()=>{save({profile,circumstances,activeStrategy,checks,fileName,isSample})},[profile,circumstances,activeStrategy,checks,fileName,isSample])
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
  function onJobsAction(action){setActiveTab('Jobs');searchJobs({role:action.role||profile.occupation,location:action.location||profile.location,dateWindow:'anyTime'})}

  function acceptJobs(payload){
    setData(prev=>({...prev,jobs:payload}))
    setSources(prev=>prev.map(s=>s.id==='jobs'?{...s,status:payload.status,cached:payload.cached,checkedAt:payload.checkedAt,freshness:payload.freshness}:s))
  }
  function jobBody(query,startIfMissing){
    return {...query,startIfMissing,profile:{occupation:profile.occupation||'',skills:profile.skills||[],experienceYears:profile.experienceYears===''||profile.experienceYears==null?null:Number(profile.experienceYears)}}
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
      const {migrationHints={},...rest}=parsed
      setProfile(p=>({...p,...rest, anzsco:parsed.anzsco||'', osca:parsed.osca||'', visa:parsed.visa||'', detectedVisa:parsed.visa||'', visaExpiry:parsed.visaExpiry||'', name:parsed.name||p.name}))
      const {found,englishNote,studyRegionalNote,...hints}=migrationHints
      setCircumstances({...emptyCircumstances,...hints,preferredStates:hints.studyState?[hints.studyState]:[]}); setIsSample(false); setChecks({}); setActiveStrategy(null)
      setScreen('profile')
    }catch(e){
      setError('I could not reach the resume parser. You can still continue with the editable demo profile.')
      setScreen('profile')
    }finally{setBusy(false)}
  }

  async function runIntelligence(){
    ++jobSequence.current; setScreen('dashboard'); setBusy(true); setData(null); setSources(initialSources.map(s=>({...s,status:'loading'})))
    const order=['migration','occupation','vacancies','jobs']
    try{
      const tasks=order.map(async (key,i)=>{
        setSources(prev=>prev.map(s=>s.id===key?{...s,status:'loading'}:s))
        const params=new URLSearchParams({
          occupation: profile.occupation||'',
          state: profile.location.split(',').pop()?.trim()||'QLD',
          anzsco: profile.anzsco||'',
          ...(key==='occupation'?{osca:profile.osca||''}:{})
        })
        if(key==='migration'){
          params.set('visa',profile.visa||'')
          params.set('experienceYears',String(profile.experienceYears||0))
          params.set('education',profile.education||'')
        }
        let payload
        try{
          const res=key==='jobs'?await fetch(`${API}/jobs/search`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(jobBody({role:profile.occupation,location:profile.location,dateWindow:'anyTime'},true)),signal:AbortSignal.timeout(90000)}):await fetch(`${API}/intelligence/${key}?${params.toString()}`,{signal:AbortSignal.timeout(90000)})
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
      const rec=await fetch(`${API}/recommend`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile,intelligence})}).then(r=>r.json())
      setData(prev=>({...prev,recommendation:rec}))
    }catch(e){setError('Some live sources could not be reached. Pathway has kept source failures visible rather than disguising them as fresh data.')}
    finally{setBusy(false)}
  }

  const migration={plan,loading:planLoading,error:planError,circumstances,setCircumstances:updateCircumstances,activeId:activeStrategy,setActiveId:setActiveStrategy,checks,toggleCheck,onJobsAction,onRefresh:()=>setPlanNonce(n=>n+1),sample:isSample,setProfile}
  if(screen==='onboarding') return <Onboarding busy={busy} error={error} fileName={fileName} onFile={parseResume} onDemo={()=>{setProfile(defaultProfile);setCircumstances(sampleCircumstances);setIsSample(true);setScreen('profile')}} saved={saved} onResume={runIntelligence}/>
  if(screen==='profile') return <ProfileReview profile={profile} setProfile={setProfile} fileName={fileName} onBack={()=>setScreen('onboarding')} onContinue={runIntelligence}/>
  return <Dashboard profile={profile} data={data} sources={sources} busy={busy} error={error} activeTab={activeTab} setActiveTab={setActiveTab} employerMode={employerMode} setEmployerMode={setEmployerMode} refresh={runIntelligence} edit={()=>setScreen('profile')} pricingOpen={pricingOpen} setPricingOpen={setPricingOpen} onJobSearch={searchJobs} migration={migration}/>
}

function Brand(){return <div className="brand"><div className="brandmark"><Compass size={20}/></div><span>Pathway</span><span className="beta">LIVE</span></div>}

function Onboarding({onFile,onDemo,busy,error,fileName,saved,onResume}){
  return <main className="landing">
    <nav><Brand/><div className="navnote"><ShieldCheck size={15}/> Built around source transparency</div></nav>
    <section className="hero">
      <div className="heroCopy">
        <div className="eyebrow"><Sparkles size={15}/> AI powered Australian career intelligence</div>
        <h1>Know the next move.<br/><span>Build a career that can stay.</span></h1>
        <p className="lead">Upload your resume and Pathway turns your experience, visa situation and goals into a personalised action plan using current Australian migration and labour market intelligence.</p>
        <div className="trustrow"><span><CircleCheck/>Career pathways</span><span><CircleCheck/>Migration signals</span><span><CircleCheck/>Live labour demand</span></div>
      </div>
      <div className="uploadCard">
        <div className="uploadIcon"><UploadCloud/></div>
        <h2>Start with your resume</h2>
        <p>PDF, DOCX or TXT. We extract your education, experience and skills, then you review everything before analysis.</p>
        <label className={`drop ${busy?'disabled':''}`}>
          <input type="file" accept=".pdf,.doc,.docx,.txt" disabled={busy} onChange={e=>e.target.files?.[0]&&onFile(e.target.files[0])}/>
          {busy?<><LoaderCircle className="spin"/> Analysing {fileName||'resume'}...</>:<><UploadCloud/> Choose resume</>}
        </label>
        {saved?.profile&&!saved.isSample&&<button className="primary resumeBtn" onClick={onResume}>Continue as {saved.profile.name||'your profile'} <ArrowUpRight size={16}/></button>}
        <button className="textBtn" onClick={onDemo}>Explore with an editable sample profile <ChevronRight size={16}/></button>
        {error&&<div className="warning"><AlertTriangle size={16}/>{error}</div>}
        <div className="privacy"><ShieldCheck size={15}/><span>Your resume is used to build your profile. Production deployment should apply encryption, retention controls and consent management.</span></div>
      </div>
    </section>
    <section className="sourceStrip"><span>Designed for live sources</span><b>Home Affairs</b><b>Jobs and Skills Australia</b><b>ABS</b><b>Job providers</b></section>
  </main>
}

function Field({label,value,onChange,type='text'}){return <label className="field"><span>{label}</span><input type={type} value={value??''} onChange={e=>onChange(type==='number'?Number(e.target.value):e.target.value)}/></label>}

const VISA_GROUPS = [
  {label:'Study and graduate', options:[
    'Student visa (subclass 500)',
    'Student Guardian visa (subclass 590)',
    'Temporary Graduate visa (subclass 485)',
    'Training visa (subclass 407)'
  ]},
  {label:'Working holiday', options:[
    'Working Holiday visa (subclass 417)',
    'Work and Holiday visa (subclass 462)'
  ]},
  {label:'Employer sponsored and temporary work', options:[
    'Skills in Demand visa (subclass 482)',
    'Employer Nomination Scheme visa (subclass 186)',
    'Skilled Employer Sponsored Regional visa (subclass 494)',
    'Temporary Work Short Stay Specialist visa (subclass 400)',
    'Temporary Work International Relations visa (subclass 403)',
    'Temporary Activity visa (subclass 408)'
  ]},
  {label:'Skilled migration', options:[
    'Skilled Independent visa (subclass 189)',
    'Skilled Nominated visa (subclass 190)',
    'Skilled Work Regional Provisional visa (subclass 491)',
    'Permanent Residence Skilled Regional visa (subclass 191)',
    'National Innovation visa (subclass 858)'
  ]},
  {label:'Family and partner', options:[
    'Partner visa onshore (subclass 820)',
    'Partner visa permanent (subclass 801)',
    'Partner visa provisional (subclass 309)',
    'Partner visa migrant (subclass 100)',
    'Prospective Marriage visa (subclass 300)',
    'Sponsored Parent Temporary visa (subclass 870)'
  ]},
  {label:'Visitor and other temporary', options:[
    'Visitor visa (subclass 600)',
    'Electronic Travel Authority (subclass 601)',
    'eVisitor (subclass 651)'
  ]},
  {label:'Bridging visas', options:[
    'Bridging visa A',
    'Bridging visa B',
    'Bridging visa C',
    'Bridging visa E'
  ]},
  {label:'Other status', options:[
    'Australian citizen',
    'Australian permanent resident',
    'Offshore with no current Australian visa',
    'Other Australian visa',
    'Unsure of current visa or status'
  ]}
]

function VisaSelect({value,onChange,detected}){
  const changed=detected && value && detected!==value
  return <label className="field visaField"><span>Current visa or status</span><select value={value||''} onChange={e=>onChange(e.target.value)}><option value="" disabled>Select your current visa or status</option>{VISA_GROUPS.map(group=><optgroup key={group.label} label={group.label}>{group.options.map(option=><option key={option} value={option}>{option}</option>)}</optgroup>)}</select><small className="fieldHint">{detected ? <>Resume detected: <b>{detected}</b>{changed ? ' · You corrected this selection. Your selection will be used for analysis.' : ' · Confirm or change it before analysis.'}</> : 'Choose the status that applies to you. Your selection is used for pathway analysis.'}</small></label>
}

function ProfileReview({profile,setProfile,onContinue,onBack,fileName}){
  const patch=(k,v)=>setProfile(p=>({...p,[k]:v,...(k==='occupation'?{anzsco:'',osca:'',roleCandidates:[{title:v}]}:{})}))
  return <main className="profilePage"><nav><Brand/><button className="ghost" onClick={onBack}>Start over</button></nav>
    <div className="stepper"><span className="done">1</span><i></i><span className="active">2</span><i></i><span>3</span><b>Resume</b><b>Review profile</b><b>Live analysis</b></div>
    <section className="profileWrap">
      <div className="sectionHeading"><div><div className="eyebrow">Profile intelligence</div><h1>Review what Pathway knows</h1><p>Correct anything before we query the Australian market. Recommendations are only as good as the profile they are based on.</p></div><div className="resumePill"><FileText size={17}/>{fileName||'Editable sample profile'}<BadgeCheck size={15}/></div></div>
      <div className="formGrid">
        <div className="formCard"><h3>Career profile</h3><Field label="Name" value={profile.name} onChange={v=>patch('name',v)}/><Field label="Current location" value={profile.location} onChange={v=>patch('location',v)}/><Field label="Target occupation" value={profile.occupation} onChange={v=>patch('occupation',v)}/><div className="two"><Field label="ANZSCO code" value={profile.anzsco} onChange={v=>patch('anzsco',v)}/><Field label="OSCA code" value={profile.osca} onChange={v=>patch('osca',v)}/></div><Field label="Qualification" value={profile.education} onChange={v=>patch('education',v)}/><Field label="Years of relevant experience" type="number" value={profile.experienceYears} onChange={v=>patch('experienceYears',v)}/></div>
        <div className="formCard"><h3>Migration context</h3><VisaSelect value={profile.visa} detected={profile.detectedVisa} onChange={v=>patch('visa',v)}/><Field label="Visa expiry if known" type="date" value={profile.visaExpiry} onChange={v=>patch('visaExpiry',v)}/><label className="field"><span>Career goal</span><textarea value={profile.goal} onChange={e=>patch('goal',e.target.value)}/></label><label className="field"><span>Skills</span><textarea value={profile.skills.join(', ')} onChange={e=>patch('skills',e.target.value.split(',').map(x=>x.trim()).filter(Boolean))}/></label><div className="infoBox"><Database size={17}/><span>Pathway will query the latest available source data after you continue. It does not treat this profile as proof of visa eligibility.</span></div></div>
      </div>
      <div className="continueBar"><div><b>Ready for live analysis</b><span>Four intelligence modules will load independently with visible freshness status.</span></div><button className="primary" onClick={onContinue}>Analyse my pathway <ArrowUpRight size={18}/></button></div>
    </section>
  </main>
}

function StatusBadge({source}){
  const labels={loading:'Loading',idle:'Waiting',fresh:source.cached?'Verified · cached':'Verified',partial:'Incomplete data',unavailable:'Unavailable',not_configured:'Not connected',stale:'Older data'}
  const good=source.status==='fresh',loading=source.status==='loading'
  return <span className={`status ${good?'fresh':loading?'loading':'bad'}`}>{loading?<LoaderCircle className="spin"/>:good?<CircleCheck/>:<AlertTriangle/>}{labels[source.status]||'Unknown status'}</span>
}

function Dashboard({profile,data,sources,busy,error,activeTab,setActiveTab,employerMode,setEmployerMode,refresh,edit,pricingOpen,setPricingOpen,onJobSearch,migration}){
  const tabs=['Overview','My pathway','Jobs','Market','Migration']
  return <div className="appShell">
    <aside><Brand/><div className="userCard"><div className="avatar">{profile.name?.charAt(0)||'P'}</div><div><b>{profile.name}</b><span>{profile.occupation}</span></div></div><div className="modeToggle"><button className={!employerMode?'selected':''} onClick={()=>setEmployerMode(false)}><Target/>Candidate</button><button className={employerMode?'selected':''} onClick={()=>setEmployerMode(true)}><Building2/>Employer</button></div><div className="sideNav">{tabs.map(t=><button key={t} className={activeTab===t?'active':''} onClick={()=>setActiveTab(t)}>{t==='Overview'?<Compass/>:t==='My pathway'?<Zap/>:t==='Jobs'?<BriefcaseBusiness/>:t==='Market'?<TrendingUp/>:<MapPinned/>}{t}</button>)}</div><div className="sideFoot"><span>Intelligence engine</span><b><i></i> Live source mode</b><small>Source failures stay visible.</small></div></aside>
    <main className="dashboard">
      <nav className="mobileTabs" aria-label="Sections">{tabs.map(t=><button key={t} className={activeTab===t?'on':''} onClick={()=>{setEmployerMode(false);setActiveTab(t)}}>{t}</button>)}</nav>
      <header><div><div className="eyebrow">{employerMode?'Employer talent intelligence':'Personal pathway intelligence'}</div><h1>{employerMode?'Find capability, not just keywords.':`Good morning, ${profile.name?.split(' ')[0]||'there'}.`}</h1><p>{employerMode?'See where international talent can close workforce gaps and what development actions improve retention.':'Here is what the Australian market means for your next move right now.'}</p></div><div className="headerActions"><button className="ghost" onClick={edit}>Edit profile</button><button className="refresh" onClick={refresh} disabled={busy}><RefreshCw className={busy?'spin':''}/> Refresh live data</button></div></header>
      <div className="freshnessPanel"><div className="freshTitle"><Database/><div><b>Live intelligence check</b><span>{busy?'Pathway is checking sources independently. Insights appear as each source responds.':'Current signals, source status and freshness in one place.'}</span></div></div><div className="sourceStatuses">{sources.map(s=><div className="sourceStatusCard" key={s.id}><div><b>{s.label}</b><span>{s.detail}</span></div><SourceInsight id={s.id} data={data} loading={s.status==='loading'}/><StatusBadge source={s}/></div>)}</div></div>
      {error&&<div className="warning wide"><AlertTriangle/>{error}</div>}
      {employerMode?<EmployerView data={data} busy={busy} profile={profile}/>:<CandidateView data={data} busy={busy} profile={profile} activeTab={activeTab} setActiveTab={setActiveTab} onUpgrade={()=>setPricingOpen(true)} onJobSearch={onJobSearch} migration={migration}/>} 
    </main>
    {pricingOpen&&<SubscriptionModal onClose={()=>setPricingOpen(false)}/>} 
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

function SubscriptionModal({onClose}){
  const plans=[
    {name:'Plus',price:'9.99',tag:'Build your evidence',features:['Personal evidence plan','Priority skill gap actions','Application readiness checklist','Saved pathway progress','Monthly pathway refresh']},
    {name:'Premium',price:'19.99',tag:'Maximise your pathway',featured:true,features:['Everything in Plus','Unlimited evidence plans','Advanced migration scenario analysis','Deeper job and market matching','Priority live intelligence refresh','Exportable pathway report']}
  ]
  return <div className="modalBackdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><div className="pricingModal"><button className="modalClose" onClick={onClose} aria-label="Close"><X/></button><div className="pricingIntro"><span className="kicker">Pathway membership</span><h2>Turn recommendations into an evidence plan</h2><p>Choose the level of guidance you want. Cancel anytime.</p></div><div className="planGrid">{plans.map(plan=><section key={plan.name} className={`planCard ${plan.featured?'featured':''}`}>{plan.featured&&<div className="popular"><Crown/> Most complete</div>}<h3>{plan.name}</h3><div className="price"><b>A${plan.price}</b><span>/ month</span></div><p>{plan.tag}</p><button className={plan.featured?'primary':'planButton'} onClick={()=>alert(`${plan.name} checkout is a demo in this prototype.`)}>Choose {plan.name}</button><div className="featureList">{plan.features.map(f=><span key={f}><Check/>{f}</span>)}</div></section>)}</div><small className="billingNote">Demo pricing only. Production checkout should use a payment provider and explicit recurring billing consent.</small></div></div>
}

function Skeleton({height=120}){return <div className="skeleton" style={{height}}><div></div><div></div><div></div></div>}
const SourceNote=({source})=><div className="sourceNote"><Clock3/> {source?.source||'Source pending'} <span>{source?.freshness||'checking'}</span></div>

function CandidateView({data,busy,profile,activeTab,setActiveTab,onUpgrade,onJobSearch,migration}){
  if(activeTab==='Migration') return <Migration {...migration} profile={profile} jobs={data?.jobs}/>
  if(!data) return <div className="cardsGrid"><Skeleton height={230}/><Skeleton height={230}/><Skeleton height={230}/><Skeleton height={320}/><Skeleton height={320}/><Skeleton height={320}/></div>
  const r=data.recommendation||{}
  if(activeTab==='My pathway') return <><PathwayView r={r}/><div className="singleView"><MigrationMilestones plan={migration.plan} activeId={migration.activeId} checks={migration.checks}/></div></>
  if(activeTab==='Jobs') return <Jobs jobs={data.jobs} profile={profile} onSearch={onJobSearch} disabled={busy}/>
  if(activeTab==='Market') return <MarketView data={data}/>
  return <Overview data={data} profile={profile} setActiveTab={setActiveTab} onUpgrade={onUpgrade} migrationCard={<MigrationSummaryCard plan={migration.plan} activeId={migration.activeId} loading={migration.loading} onOpen={()=>setActiveTab('Migration')}/>}/>
}

function Metric({icon,label,value,sub,strong}) {return <div className={`metric ${strong?'strong':''}`}><div className="metricIcon">{icon}</div><span>{label}</span><b>{value}</b><small>{sub}</small></div>}
function SignalMetric({icon,label,value,sub,facts=[]}) {return <div className="metric signalMetric"><div className="metricIcon">{icon}</div><span>{label}</span><b>{value}</b><small>{sub}</small>{facts.length>0&&<div className="metricFacts">{facts.slice(0,2).map((f,i)=><div key={i}>{f}</div>)}</div>}</div>}
function PathwayView({r}){return <div className="singleView"><div className="viewTitle"><span className="kicker">Decision support</span><h2>Your recommended pathway</h2><p>The highlighted step changes with your profile evidence. Completed stages reflect evidence Pathway can already establish from the information you provided.</p></div><div className="roadmap">{(r.pathway||[]).map((p,i)=><div className={`roadStep ${p.status||''}`} key={i}><div className="stepNum">{p.status==='complete'?<CircleCheck/>:i+1}</div><div><span>{p.status==='current'?'Current step':p.status==='complete'?'Evidence present':p.horizon}</span><h3>{p.title}</h3><p>{p.detail}</p><button onClick={()=>alert('Detailed checklist is available through Build Evidence Plan in this prototype.')}>Open checklist <ChevronRight/></button></div><div className="confidence">{p.confidence||'High'} confidence</div></div>)}</div></div>}
function MarketView({data}){return <div className="singleView"><div className="viewTitle"><span className="kicker">Power BI style market lens</span><h2>Understand the market around your occupation</h2></div><div className="marketGrid"><section className="card chartCard wideCard"><h3>Internet vacancy trend</h3><div className="chart tall"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.vacancies?.trend||[]}><CartesianGrid vertical={false} stroke="rgba(20,30,35,.08)"/><XAxis dataKey="month" axisLine={false} tickLine={false}/><YAxis/><Tooltip/><Bar dataKey="value" fill="currentColor" radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></div><SourceNote source={data.vacancies}/></section><section className="card"><h3>Occupation signal</h3><div className="bigStat">{data.occupation?.shortage||'Not available'}</div><p>{data.occupation?.shortageNote}</p><hr/><b>{data.occupation?.employment||'Employment data pending'}</b><span className="muted">{data.occupation?.earnings||''}</span><SourceNote source={data.occupation}/></section></div></div>}
function EmployerView({data,profile}){return <div className="singleView"><div className="viewTitle"><span className="kicker">Employer lens</span><h2>Turn international talent into workforce capacity</h2><p>This demo uses the same market intelligence to show employers where skills are scarce, which adjacent talent could fit, and what development support would close the gap.</p></div><div className="metricGrid"><Metric icon={<Users/>} label="Talent pool" value="24" sub="Illustrative matched candidates"/><Metric icon={<Target/>} label="Target capability" value={profile.occupation} sub="Current search lens"/><Metric icon={<TrendingUp/>} label="Market pressure" value={data?.occupation?.shortage||'Checking'} sub="JSA shortage signal"/><Metric icon={<Zap/>} label="Developable matches" value="11" sub="Could close gaps within 90 days"/></div><section className="card employerTable"><div className="cardHead"><div><span className="kicker">Capability based shortlist</span><h2>International talent worth developing</h2></div><span className="livePill"><i></i> Privacy safe demo</span></div>{['Embedded Engineer','Automation Graduate','Systems Engineer','Firmware Developer'].map((role,i)=><div className="candidate" key={role}><div className="avatar small">{['AL','MK','SP','JN'][i]}</div><div><b>Candidate {String.fromCharCode(65+i)}</b><span>{role} · {['QLD','VIC','NSW','SA'][i]}</span></div><div className="skillTags"><span>{['C++','PLC','Python','RTOS'][i]}</span><span>{['Controls','CAD','Systems','Electronics'][i]}</span></div><div className="match"><b>{[92,88,84,81][i]}%</b><span>capability</span></div><button>View evidence</button></div>)}</section></div>}

createRoot(document.getElementById('root')).render(<App/>)
