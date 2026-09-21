import React, {useEffect, useMemo, useState} from 'react'
import {createRoot} from 'react-dom/client'
import {AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar} from 'recharts'
import {UploadCloud, Sparkles, Compass, BriefcaseBusiness, MapPinned, BadgeCheck, RefreshCw, Clock3, Database, ChevronRight, FileText, CircleCheck, AlertTriangle, Search, Building2, TrendingUp, ShieldCheck, ArrowUpRight, Zap, Users, Target, LoaderCircle, ExternalLink, X, Check, Crown} from 'lucide-react'
import './styles.css'

const API = '/api'

const defaultProfile = {
  name: 'Your profile', location: 'Brisbane, QLD', visa: 'Student visa (subclass 500)', detectedVisa: 'Student visa (subclass 500)', visaExpiry: '',
  occupation: 'Mechatronics Engineer', careerFamily: 'Mechatronics and automation', anzsco: '233999', osca: '233999',
  roleCandidates: [{title:'Mechatronics Engineer'},{title:'Automation Engineer'},{title:'Controls Engineer'},{title:'Robotics Engineer'}],
  education: 'Bachelor of Engineering', experienceYears: 1, skills: ['Embedded systems','C++','Python','Control systems','CAD'],
  goal: 'Build an engineering career and understand realistic skilled migration options'
}

const initialSources = [
  {id:'migration', label:'SkillSelect invitation data', detail:'Department of Home Affairs', status:'idle'},
  {id:'occupation', label:'Occupation and shortage intelligence', detail:'Jobs and Skills Australia', status:'idle'},
  {id:'vacancies', label:'Australian vacancy demand', detail:'JSA Internet Vacancy Index', status:'idle'},
  {id:'jobs', label:'Relevant open roles', detail:'Configured job providers', status:'idle'}
]

function App(){
  const [screen,setScreen]=useState('onboarding')
  const [profile,setProfile]=useState(defaultProfile)
  const [sources,setSources]=useState(initialSources)
  const [data,setData]=useState(null)
  const [busy,setBusy]=useState(false)
  const [fileName,setFileName]=useState('')
  const [error,setError]=useState('')
  const [activeTab,setActiveTab]=useState('Overview')
  const [employerMode,setEmployerMode]=useState(false)
  const [pricingOpen,setPricingOpen]=useState(false)

  async function parseResume(file){
    setBusy(true); setError(''); setFileName(file.name)
    try{
      const body=new FormData(); body.append('file',file)
      const res=await fetch(`${API}/profile/parse-resume`,{method:'POST',body})
      if(!res.ok) throw new Error('Resume analysis failed')
      const parsed=await res.json()
      setProfile(p=>({...p,...parsed, detectedVisa: parsed.visa || p.detectedVisa || '', name:parsed.name||p.name}))
      setScreen('profile')
    }catch(e){
      setError('I could not reach the resume parser. You can still continue with the editable demo profile.')
      setScreen('profile')
    }finally{setBusy(false)}
  }

  async function runIntelligence(){
    setScreen('dashboard'); setBusy(true); setData(null); setSources(initialSources.map(s=>({...s,status:'loading'})))
    const order=['migration','occupation','vacancies','jobs']
    try{
      const tasks=order.map(async (key,i)=>{
        await new Promise(r=>setTimeout(r,i*420))
        setSources(prev=>prev.map(s=>s.id===key?{...s,status:'loading'}:s))
        const params=new URLSearchParams({
          occupation: profile.occupation||'',
          state: profile.location.split(',').pop()?.trim()||'QLD',
          anzsco: profile.anzsco||''
        })
        if(key==='migration'){
          params.set('visa',profile.visa||'')
          params.set('experienceYears',String(profile.experienceYears||0))
          params.set('education',profile.education||'')
        }
        if(key==='jobs'){
          params.set('skills',(profile.skills||[]).join(','))
          params.set('education',profile.education||'')
          params.set('goal',profile.goal||'')
          params.set('candidates',(profile.roleCandidates||[]).map(r=>typeof r==='string'?r:r.title).filter(Boolean).join('|'))
        }
        const res=await fetch(`${API}/intelligence/${key}?${params.toString()}`)
        const payload=await res.json()
        setSources(prev=>prev.map(s=>s.id===key?{...s,status:payload.status||'fresh', updated:payload.updated, freshness:payload.freshness}:s))
        setData(prev=>({...((prev&&typeof prev==='object')?prev:{}),[key]:payload}))
        return [key,payload]
      })
      const entries=await Promise.all(tasks)
      const intelligence=Object.fromEntries(entries)
      const rec=await fetch(`${API}/recommend`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile,intelligence})}).then(r=>r.json())
      setData({...intelligence,recommendation:rec})
    }catch(e){setError('Some live sources could not be reached. Pathway has kept source failures visible rather than disguising them as fresh data.')}
    finally{setBusy(false)}
  }

  if(screen==='onboarding') return <Onboarding busy={busy} error={error} fileName={fileName} onFile={parseResume} onDemo={()=>setScreen('profile')}/>
  if(screen==='profile') return <ProfileReview profile={profile} setProfile={setProfile} fileName={fileName} onBack={()=>setScreen('onboarding')} onContinue={runIntelligence}/>
  return <Dashboard profile={profile} data={data} sources={sources} busy={busy} error={error} activeTab={activeTab} setActiveTab={setActiveTab} employerMode={employerMode} setEmployerMode={setEmployerMode} refresh={runIntelligence} edit={()=>setScreen('profile')} pricingOpen={pricingOpen} setPricingOpen={setPricingOpen}/>
}

function Brand(){return <div className="brand"><div className="brandmark"><Compass size={20}/></div><span>Pathway</span><span className="beta">LIVE</span></div>}

function Onboarding({onFile,onDemo,busy,error,fileName}){
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
  const patch=(k,v)=>setProfile(p=>({...p,[k]:v}))
  return <main className="profilePage"><nav><Brand/><button className="ghost" onClick={onBack}>Start over</button></nav>
    <div className="stepper"><span className="done">1</span><i></i><span className="active">2</span><i></i><span>3</span><b>Resume</b><b>Review profile</b><b>Live analysis</b></div>
    <section className="profileWrap">
      <div className="sectionHeading"><div><div className="eyebrow">Profile intelligence</div><h1>Review what Pathway knows</h1><p>Correct anything before we query the Australian market. Recommendations are only as good as the profile they are based on.</p></div><div className="resumePill"><FileText size={17}/>{fileName||'Editable sample profile'}<BadgeCheck size={15}/></div></div>
      <div className="formGrid">
        <div className="formCard"><h3>Career profile</h3><Field label="Name" value={profile.name} onChange={v=>patch('name',v)}/><Field label="Current location" value={profile.location} onChange={v=>patch('location',v)}/><Field label="Target occupation" value={profile.occupation} onChange={v=>patch('occupation',v)}/><div className="two"><Field label="ANZSCO code" value={profile.anzsco} onChange={v=>patch('anzsco',v)}/><Field label="OSCA code" value={profile.osca} onChange={v=>patch('osca',v)}/></div><Field label="Qualification" value={profile.education} onChange={v=>patch('education',v)}/><Field label="Years of relevant experience" type="number" value={profile.experienceYears} onChange={v=>patch('experienceYears',v)}/></div>
        <div className="formCard"><h3>Migration context</h3><VisaSelect value={profile.visa} detected={profile.detectedVisa} onChange={v=>patch('visa',v)}/><Field label="Visa expiry if known" value={profile.visaExpiry} onChange={v=>patch('visaExpiry',v)}/><label className="field"><span>Career goal</span><textarea value={profile.goal} onChange={e=>patch('goal',e.target.value)}/></label><label className="field"><span>Skills</span><textarea value={profile.skills.join(', ')} onChange={e=>patch('skills',e.target.value.split(',').map(x=>x.trim()).filter(Boolean))}/></label><div className="infoBox"><Database size={17}/><span>Pathway will query the latest available source data after you continue. It does not treat this profile as proof of visa eligibility.</span></div></div>
      </div>
      <div className="continueBar"><div><b>Ready for live analysis</b><span>Four intelligence modules will load independently with visible freshness status.</span></div><button className="primary" onClick={onContinue}>Analyse my pathway <ArrowUpRight size={18}/></button></div>
    </section>
  </main>
}

function StatusBadge({source}){
  const loading=source.status==='loading', failed=source.status==='unavailable', cached=source.status==='cached'
  return <span className={`status ${failed?'bad':cached?'cached':loading?'loading':'fresh'}`}>{loading?<LoaderCircle className="spin"/>:failed?<AlertTriangle/>:<CircleCheck/>}{loading?'Checking now':failed?'Source unavailable':cached?'Recent cache':'Fresh'}{source.updated&&!loading&&<small>{source.updated}</small>}</span>
}

function Dashboard({profile,data,sources,busy,error,activeTab,setActiveTab,employerMode,setEmployerMode,refresh,edit,pricingOpen,setPricingOpen}){
  const tabs=['Overview','My pathway','Jobs','Market','Migration']
  return <div className="appShell">
    <aside><Brand/><div className="userCard"><div className="avatar">{profile.name?.charAt(0)||'P'}</div><div><b>{profile.name}</b><span>{profile.occupation}</span></div></div><div className="modeToggle"><button className={!employerMode?'selected':''} onClick={()=>setEmployerMode(false)}><Target/>Candidate</button><button className={employerMode?'selected':''} onClick={()=>setEmployerMode(true)}><Building2/>Employer</button></div><div className="sideNav">{tabs.map(t=><button key={t} className={activeTab===t?'active':''} onClick={()=>setActiveTab(t)}>{t==='Overview'?<Compass/>:t==='My pathway'?<Zap/>:t==='Jobs'?<BriefcaseBusiness/>:t==='Market'?<TrendingUp/>:<MapPinned/>}{t}</button>)}</div><div className="sideFoot"><span>Intelligence engine</span><b><i></i> Live source mode</b><small>Source failures stay visible.</small></div></aside>
    <main className="dashboard">
      <header><div><div className="eyebrow">{employerMode?'Employer talent intelligence':'Personal pathway intelligence'}</div><h1>{employerMode?'Find capability, not just keywords.':`Good morning, ${profile.name?.split(' ')[0]||'there'}.`}</h1><p>{employerMode?'See where international talent can close workforce gaps and what development actions improve retention.':'Here is what the Australian market means for your next move right now.'}</p></div><div className="headerActions"><button className="ghost" onClick={edit}>Edit profile</button><button className="refresh" onClick={refresh} disabled={busy}><RefreshCw className={busy?'spin':''}/> Refresh live data</button></div></header>
      <div className="freshnessPanel"><div className="freshTitle"><Database/><div><b>Live intelligence check</b><span>{busy?'Pathway is checking sources independently. Insights appear as each source responds.':'Current signals, source status and freshness in one place.'}</span></div></div><div className="sourceStatuses">{sources.map(s=><div className="sourceStatusCard" key={s.id}><div><b>{s.label}</b><span>{s.detail}</span></div><SourceInsight id={s.id} data={data} loading={s.status==='loading'}/><StatusBadge source={s}/></div>)}</div></div>
      {error&&<div className="warning wide"><AlertTriangle/>{error}</div>}
      {employerMode?<EmployerView data={data} busy={busy} profile={profile}/>:<CandidateView data={data} busy={busy} profile={profile} activeTab={activeTab} setActiveTab={setActiveTab} onUpgrade={()=>setPricingOpen(true)}/>} 
    </main>
    {pricingOpen&&<SubscriptionModal onClose={()=>setPricingOpen(false)}/>} 
  </div>
}


function SourceInsight({id,data,loading}){
  if(loading && !data?.[id]) return <div className="sourceInsight loadingInsight"><LoaderCircle className="spin"/><span>Retrieving current data…</span></div>
  const d=data?.[id]
  if(!d) return <div className="sourceInsight"><strong>Waiting for analysis</strong><span>Results will appear here.</span></div>
  if(id==='migration') return <div className="sourceInsight"><strong>{d.latestRound?.scoreForOccupation||d.latestRound?.date||'Round checked'}</strong><span>{d.latestRound?.scoreForOccupation?`Occupation score · ${d.latestRound?.invitations||'published'} invitations`:[d.latestRound?.invitations&&`${d.latestRound.invitations} invitations`,d.nextRound&&`next by ${d.nextRound}`].filter(Boolean).join(' · ')||'Official round data checked'}</span></div>
  if(id==='occupation') return <div className="sourceInsight"><strong>{d.occupationMatch?'Occupation in shortage':(d.shortage||'Occupation checked')}</strong><span>{d.occupationMatch?`${d.occupationChecked} matched the current OSL.`:[d.oslYear&&`${d.oslYear} OSL`,d.nationalShortagePct&&`${d.nationalShortagePct} nationally`,d.vacancyFillRate&&`${d.vacancyFillRate} fill rate`].filter(Boolean).join(' · ')||'Current JSA shortage sources checked.'}</span></div>
  if(id==='vacancies') return <div className="sourceInsight"><strong>{d.releasePeriod||d.headline||'IVI checked'}</strong><span>{[d.releaseDate&&`Released ${d.releaseDate}`,d.nextReleaseDate&&`next ${d.nextReleaseDate}`].filter(Boolean).join(' · ')||d.subheadline||'Australian vacancy demand updated.'}</span></div>
  if(id==='jobs') return <div className="sourceInsight"><strong>{d.count??d.roles?.length??0} relevant roles</strong><span>{d.roles?.[0]?.title?`Top match: ${d.roles[0].title} · ${d.roles[0].match||'—'}% fit`:(d.note||'Current role search completed.')}</span></div>
  return null
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

function CandidateView({data,busy,profile,activeTab,setActiveTab,onUpgrade}){
  if(!data) return <div className="cardsGrid"><Skeleton height={230}/><Skeleton height={230}/><Skeleton height={230}/><Skeleton height={320}/><Skeleton height={320}/><Skeleton height={320}/></div>
  const r=data.recommendation||{}
  if(activeTab==='My pathway') return <PathwayView r={r}/>
  if(activeTab==='Jobs') return <JobsView data={data}/>
  if(activeTab==='Market') return <MarketView data={data}/>
  if(activeTab==='Migration') return <MigrationView data={data} profile={profile}/>
  return <>
    <div className="metricGrid">
      <Metric icon={<Target/>} label="Pathway readiness" value={`${r.readiness||68}%`} sub={r.readinessLabel||'Building evidence'} strong/>
      <SignalMetric icon={<BriefcaseBusiness/>} label="Vacancy signal" value={data.vacancies?.releasePeriod||data.vacancies?.headline||'Checking'} sub={data.vacancies?.releaseDate?`IVI released ${data.vacancies.releaseDate}`:(data.vacancies?.subheadline||'Australian demand')} facts={[data.vacancies?.nextReleaseDate&&`Next release ${data.vacancies.nextReleaseDate}`,data.vacancies?.coverage].filter(Boolean)} />
      <SignalMetric icon={<TrendingUp/>} label="Shortage signal" value={data.occupation?.occupationMatch?'In shortage':(data.occupation?.shortage||'Checking')} sub={data.occupation?.occupationMatch?`${profile.occupation} matched current OSL`:data.occupation?.oslYear?`${data.occupation.oslYear} OSL checked for ${profile.occupation}`:(data.occupation?.shortageNote||'Occupation assessment')} facts={[data.occupation?.occupationResult?.stateRating&&`${data.occupation.occupationResult.state}: ${data.occupation.occupationResult.stateRating}`,data.occupation?.nationalShortagePct&&`${data.occupation.nationalShortagePct} of assessed occupations in national shortage`,data.occupation?.vacancyFillRate&&`Latest national vacancy fill rate ${data.occupation.vacancyFillRate}`].filter(Boolean)} />
      <SignalMetric icon={<MapPinned/>} label="Latest 189 round" value={data.migration?.latestRound?.scoreForOccupation||data.migration?.latestRound?.invitations&&`${data.migration.latestRound.invitations} invites`||'See details'} sub={data.migration?.latestRound?.date?`Round ${data.migration.latestRound.date}`:'Home Affairs'} facts={[data.migration?.latestRound?.scoreForOccupation&&`${profile.occupation} minimum score published`,data.migration?.nextRound&&`Next round expected by ${data.migration.nextRound}`,data.migration?.programYear189Invitations&&`${data.migration.programYear189Invitations} subclass 189 invitations this program year`].filter(Boolean)} />
    </div>
    <div className="mainGrid">
      <section className="card priority"><div className="cardHead"><div><span className="kicker">Highest impact next move</span><h2>{r.topAction?.title||'Build relevant Australian evidence'}</h2></div><span className="impact">+{r.topAction?.impact||18} opportunity</span></div><p>{r.topAction?.why||'This action improves both employability evidence and future pathway optionality.'}</p><div className="actionRow"><button className="primary" onClick={onUpgrade}>Build Evidence Plan <ChevronRight/></button><span><Clock3/> {r.topAction?.time||'Next 30 days'}</span></div></section>
      <section className="card blockers"><div className="cardHead"><div><span className="kicker">What is holding you back</span><h2>Current blockers</h2></div><AlertTriangle/></div>{(r.blockers||[]).slice(0,3).map((b,i)=><div className="blocker" key={i}><span>{i+1}</span><div><b>{b.title}</b><p>{b.detail}</p></div><em>{b.severity||'Medium'}</em></div>)}</section>
      <section className="card pathwayCard"><div className="cardHead"><div><span className="kicker">Recommended route</span><h2>Your pathway map</h2></div><Compass/></div><div className="timeline">{(r.pathway||[]).slice(0,4).map((p,i)=><div key={i} className={p.status==='current'?'now':p.status==='complete'?'complete':''}><span>{p.status==='complete'?'DONE':p.status==='current'?'NOW':String(i+1).padStart(2,'0')}</span><div><b>{p.title}</b><p>{p.detail}</p></div><small>{p.horizon}</small></div>)}</div><button className="textBtn" onClick={()=>setActiveTab('My pathway')}>Open full pathway <ChevronRight/></button></section>
      <section className="card chartCard"><div className="cardHead"><div><span className="kicker">Labour market</span><h2>Vacancy trend</h2></div><SourceNote source={data.vacancies}/></div><div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.vacancies?.trend||[]}><defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="currentColor" stopOpacity={.24}/><stop offset="100%" stopColor="currentColor" stopOpacity={0}/></linearGradient></defs><CartesianGrid vertical={false} stroke="rgba(20,30,35,.08)"/><XAxis dataKey="month" axisLine={false} tickLine={false}/><YAxis hide/><Tooltip/><Area type="monotone" dataKey="value" stroke="currentColor" strokeWidth={2.5} fill="url(#fill)"/></AreaChart></ResponsiveContainer></div></section>
      <section className="card jobsCard"><div className="cardHead"><div><span className="kicker">Opportunity radar</span><h2>Roles worth targeting</h2></div><SourceNote source={data.jobs}/></div>{(data.jobs?.roles||[]).slice(0,4).map((j,i)=><div className="job" key={i}><div className="jobLogo">{j.company?.charAt(0)||'A'}</div><div><b>{j.title}</b><span>{j.company} · {j.location}</span></div><div className="match"><b>{j.match||'82'}%</b><span>fit</span></div></div>)}</section>
    </div>
  </>
}

function Metric({icon,label,value,sub,strong}) {return <div className={`metric ${strong?'strong':''}`}><div className="metricIcon">{icon}</div><span>{label}</span><b>{value}</b><small>{sub}</small></div>}
function SignalMetric({icon,label,value,sub,facts=[]}) {return <div className="metric signalMetric"><div className="metricIcon">{icon}</div><span>{label}</span><b>{value}</b><small>{sub}</small>{facts.length>0&&<div className="metricFacts">{facts.slice(0,2).map((f,i)=><div key={i}>{f}</div>)}</div>}</div>}
function PathwayView({r}){return <div className="singleView"><div className="viewTitle"><span className="kicker">Decision support</span><h2>Your recommended pathway</h2><p>The highlighted step changes with your profile evidence. Completed stages reflect evidence Pathway can already establish from the information you provided.</p></div><div className="roadmap">{(r.pathway||[]).map((p,i)=><div className={`roadStep ${p.status||''}`} key={i}><div className="stepNum">{p.status==='complete'?<CircleCheck/>:i+1}</div><div><span>{p.status==='current'?'Current step':p.status==='complete'?'Evidence present':p.horizon}</span><h3>{p.title}</h3><p>{p.detail}</p><button onClick={()=>alert('Detailed checklist is available through Build Evidence Plan in this prototype.')}>Open checklist <ChevronRight/></button></div><div className="confidence">{p.confidence||'High'} confidence</div></div>)}</div></div>}
function JobsView({data}){return <div className="singleView"><div className="viewTitle"><span className="kicker">Current opportunity market</span><h2>Roles that move your pathway forward</h2><p>Ranking combines skill relevance, evidence value and available job feed data.</p></div><div className="jobList">{(data.jobs?.roles||[]).map((j,i)=><div className="jobBig" key={i}><div className="jobLogo big">{j.company?.charAt(0)||'A'}</div><div className="jobInfo"><b>{j.title}</b><span>{j.company} · {j.location}</span><p>{j.reason||'Relevant to your target occupation and skill profile.'}</p></div><div className="match"><b>{j.match||80}%</b><span>pathway fit</span></div><button><ExternalLink/></button></div>)}</div><SourceNote source={data.jobs}/></div>}
function MarketView({data}){return <div className="singleView"><div className="viewTitle"><span className="kicker">Power BI style market lens</span><h2>Understand the market around your occupation</h2></div><div className="marketGrid"><section className="card chartCard wideCard"><h3>Internet vacancy trend</h3><div className="chart tall"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.vacancies?.trend||[]}><CartesianGrid vertical={false} stroke="rgba(20,30,35,.08)"/><XAxis dataKey="month" axisLine={false} tickLine={false}/><YAxis/><Tooltip/><Bar dataKey="value" fill="currentColor" radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></div><SourceNote source={data.vacancies}/></section><section className="card"><h3>Occupation signal</h3><div className="bigStat">{data.occupation?.shortage||'Not available'}</div><p>{data.occupation?.shortageNote}</p><hr/><b>{data.occupation?.employment||'Employment data pending'}</b><span className="muted">{data.occupation?.earnings||''}</span><SourceNote source={data.occupation}/></section></div></div>}
function MigrationView({data,profile}){
  const m=data.migration||{}
  const routes=m.pathways||[]
  return <div className="singleView">
    <div className="viewTitle"><span className="kicker">Migration intelligence</span><h2>Your realistic migration options, compared</h2><p>189 is one signal, not the whole strategy. Pathway compares points tested, state, employer, regional, graduate and specialist routes against your current profile.</p></div>
    <div className="migrationSummary">
      <section className="card"><span className="kicker">Current context</span><div className="bigStat compactStat">{profile.visa||'Not confirmed'}</div><p>{m.currentVisaContext?.settled?'You already hold a settled status, so migration optimisation is not required. Career progression should take priority.':`Current analysis for ${profile.occupation}. Your selected visa, experience and occupation shape the ranking below.`}</p></section>
      <section className="card"><span className="kicker">Latest 189 evidence</span><div className="bigStat">{m.latestRound?.scoreForOccupation||m.latestRound?.date||'Checking'}</div><p>{m.latestRound?.scoreForOccupation?`${profile.occupation} had an occupation score published in the latest captured round.`:(m.latestRound?.headline||'Latest official invitation outcomes checked.')}</p><div className="fact"><span>Round date</span><b>{m.latestRound?.date||'See source'}</b></div><div className="fact"><span>Total 189 invitations</span><b>{m.latestRound?.invitations||'See source'}</b></div><SourceNote source={m}/></section>
      <section className="card interpretationCard"><span className="kicker">Pathway interpretation</span><h3>{m.interpretation?.title||'Compare multiple routes'}</h3><p>{m.interpretation?.detail}</p><div className="infoBox"><ShieldCheck/><span>These are decision support signals, not visa eligibility decisions. Verify current criteria on Home Affairs and relevant state or territory sites before acting.</span></div></section>
    </div>
    {m.currentVisaContext?.settled?<section className="card settledCard"><BadgeCheck/><div><h3>No migration pathway required</h3><p>Your selected status indicates permanent residence or citizenship. Pathway should now optimise career opportunity, salary, skill development and employer fit instead.</p></div></section>:<section className="card routeMatrix"><div className="cardHead"><div><span className="kicker">Personalised route matrix</span><h2>Which pathways deserve attention</h2></div><span className="livePill"><i></i> Profile ranked</span></div><div className="routeList">{routes.map((r,i)=><article className="visaRoute" key={r.code}><div className="routeRank">{i+1}</div><div className="routeMain"><div className="routeTitle"><div><b>{r.code}</b><h3>{r.name}</h3></div><span className={`routeStatus ${r.status?.toLowerCase().replaceAll(' ','')}`}>{r.status}</span></div><p>{r.summary}</p><div className="routeReason"><Target/><span>{r.reason}</span></div><div className="routeNeeds"><span>What it generally needs</span><b>{r.needs}</b></div></div><a className="routeLink" href={r.url} target="_blank" rel="noreferrer" aria-label={`Open official ${r.code} information`}><ExternalLink/></a></article>)}</div><SourceNote source={m}/></section>}
  </div>
}
function EmployerView({data,profile}){return <div className="singleView"><div className="viewTitle"><span className="kicker">Employer lens</span><h2>Turn international talent into workforce capacity</h2><p>This demo uses the same market intelligence to show employers where skills are scarce, which adjacent talent could fit, and what development support would close the gap.</p></div><div className="metricGrid"><Metric icon={<Users/>} label="Talent pool" value="24" sub="Illustrative matched candidates"/><Metric icon={<Target/>} label="Target capability" value={profile.occupation} sub="Current search lens"/><Metric icon={<TrendingUp/>} label="Market pressure" value={data?.occupation?.shortage||'Checking'} sub="JSA shortage signal"/><Metric icon={<Zap/>} label="Developable matches" value="11" sub="Could close gaps within 90 days"/></div><section className="card employerTable"><div className="cardHead"><div><span className="kicker">Capability based shortlist</span><h2>International talent worth developing</h2></div><span className="livePill"><i></i> Privacy safe demo</span></div>{['Embedded Engineer','Automation Graduate','Systems Engineer','Firmware Developer'].map((role,i)=><div className="candidate" key={role}><div className="avatar small">{['AL','MK','SP','JN'][i]}</div><div><b>Candidate {String.fromCharCode(65+i)}</b><span>{role} · {['QLD','VIC','NSW','SA'][i]}</span></div><div className="skillTags"><span>{['C++','PLC','Python','RTOS'][i]}</span><span>{['Controls','CAD','Systems','Electronics'][i]}</span></div><div className="match"><b>{[92,88,84,81][i]}%</b><span>capability</span></div><button>View evidence</button></div>)}</section></div>}

createRoot(document.getElementById('root')).render(<App/>)
