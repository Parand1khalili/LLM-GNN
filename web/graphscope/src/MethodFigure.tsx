import { useState } from 'react';

const explanations: Record<string,string> = {
  input:'The exact admitted Cora topology contains 2,708 nodes and 5,278 unique undirected edges. Text and annotations cover a smaller frozen research cohort. No ground-truth labels enter annotation or routing.',
  selection:'The historical FeatProp cohort contains 140 fixed targets. Primary 135 and Sensitivity 140 are distinct evaluation cohorts; PageRank2 is a separate historical study.',
  b1:'B1 sees target text only. Narrative v0 sees target text plus the authentic selected local evidence. Both use the same underlying LLM and three historical samples per arm.',
  narrative:'Only recorded selected neighborhood evidence entered the historical Narrative prompt. Admitting full topology now does not retroactively expand that prompt.',
  vote:'Stored parsed samples produce separate voted labels and confidence for each arm. Frozen parsed-sample replay is distinct from parsing original raw responses.',
  filter:'PS and noPS are separate historical conditions. CE and confidence-weighted CE are also distinct. They must not be pooled as one result.',
  gcn:'Historical GCN outcomes use matched seeds 0–9 and fixed protocols. Saved accuracy is the primary scientific endpoint, not annotation confidence.',
  route:'SARA-2 confidence/agreement routing and optional judge are a separate extension. SARA-3 adds R0, lexical semantic legacy, and prospective R1/R2 routing variants. This figure does not imply all variants ran for this node.',
  blind:'Rich Prompt V2 blind verification sees authorized article evidence and public class semantics, without B1/Narrative candidate labels in the first pass.',
  l1:'Schema and exact evidence checks establish provenance, not semantic validity. Invalid evidence is rejected. A valid abstention skips comparison.',
  compare:'Comparison is permitted only for a valid non-abstaining blind result and a protocol that authorizes it. Some scopes queue L2 before comparison; blind-only amendments prohibit comparison.',
  arbitration:'Conservative arbitration or abstention follows validated responses and the selected protocol. Automated concordance can yield an unvalidated proposal; it is not independent L2 approval or a training label.',
  future:'SARA downstream training requires separate label admission and a frozen controlled protocol. No new SARA GCN improvement is established by this public snapshot.',
  stop:'Rejection, abstention and pending semantic review remain explicit outcomes. They do not silently become accepted training labels.',
};

export function MethodFigure({ onStage, onAgents }: { onStage:(stage:number)=>void; onAgents:()=>void }) {
  const [active,setActive]=useState('input');
  const choose=(id:string,stage?:number)=>{setActive(id);if(stage!==undefined)onStage(stage);};
  const box=(id:string,x:number,y:number,w:number,title:string,lines:string[],tone='neutral',stage?:number)=>
    <g key={id} className={`method-node ${tone} ${active===id?'selected':''}`} role="button" tabIndex={0} aria-label={`Inspect ${title}`} aria-pressed={active===id} onClick={()=>choose(id,stage)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(id,stage);}}}>
      <rect x={x} y={y} width={w} height={86} rx="3"/><text x={x+14} y={y+27} className="node-title">{title}</text>{lines.map((line,i)=><text key={line} x={x+14} y={y+49+i*17} className="node-note">{line}</text>)}
    </g>;
  return <figure className="method-figure">
    <div className="method-figure-title"><h2>From graph evidence to a training decision</h2><span>Method map · select a stage to inspect</span></div>
    <div className="method-map-scroll" tabIndex={0} role="region" aria-label="Scrollable method flowchart">
      <svg viewBox="0 0 1200 780" role="group" aria-labelledby="method-map-title method-map-desc">
        <title id="method-map-title">LLM-GNN historical comparison and separate SARA research extension</title>
        <desc id="method-map-desc">Cora and target selection split into text-only B1 and graph-aware Narrative. Both feed separate voting, optional filtering and historical GCN evaluation. A separate SARA branch routes frozen pairs through blind verification, L1 validation, conditional comparison and conservative arbitration. Rejection, abstention or pending L2 do not become training labels. Future SARA GCN requires separate admission.</desc>
        <defs><marker id="method-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 10 5 0 10Z" fill="context-stroke"/></marker></defs>
        <text x="20" y="32" className="lane-title">Historical comparison</text><text x="20" y="54" className="lane-note">Recorded FeatProp study · same LLM · matched downstream protocols</text>
        <g className="method-links"><path d="M190 180H215"/><path d="M390 180H412V123H440"/><path d="M412 180V245H440"/><path className="b1-link" d="M650 123H682V180H705"/><path className="narrative-link" d="M650 245H682V180"/><path d="M875 180H900"/><path d="M1040 180H1065"/></g>
        {box('input',20,137,170,'Cora + text',['Verified topology','GT isolated'])}
        {box('selection',215,137,175,'Select targets',['FeatProp · 140 targets','Frozen global node IDs'],'neutral',0)}
        {box('b1',440,80,210,'B1 · text only',['Target article text','3 samples'],'b1',2)}
        {box('narrative',440,202,210,'Narrative v0',['Text + selected neighbors','Recorded local evidence'],'narrative',1)}
        {box('vote',705,137,170,'Parse & vote',['Separate frozen labels','Per-arm confidence'],'neutral',2)}
        {box('filter',900,137,140,'PS / noPS',['Separate conditions','CE / WCE'],'neutral',3)}
        {box('gcn',1065,137,115,'GCN',['Seeds 0–9','Saved accuracy'],'neutral',4)}
        <path d="M20 325H1180" className="lane-divider"/>
        <text x="20" y="361" className="lane-title">SARA · separate research extension</text><text x="20" y="383" className="lane-note">Implemented roles · individual execution and evidence status depend on the admitted run</text>
        <g className="method-links extension"><path d="M790 223V306H105V425"/><path d="M190 468H220"/><path d="M420 468H450"/><path d="M640 468H675"/><path d="M900 468H935"/><path d="M545 511V600H650"/><path d="M1050 511V643H900"/><path d="M1180 468H1192V699H1180"/></g>
        <text x="310" y="300" className="edge-note">Frozen annotation pairs + authorized evidence</text>
        {box('route',20,425,170,'Route review',['SARA-2 / SARA-3','R0 · R1 · R2 variants'])}
        {box('blind',220,425,200,'Blind verification',['Rich Prompt V2','Candidates withheld'],'b1')}
        {box('l1',450,425,190,'L1 evidence gate',['Schema + exact quotes','Valid non-abstaining?'])}
        {box('compare',675,425,225,'Conditional comparison',['Only if protocol permits','L2 may be required first'])}
        {box('arbitration',935,425,245,'Conservative arbitration',['Proposal / abstention','Concordance is not L2'])}
        <text x="650" y="455" className="edge-note">Yes</text><text x="555" y="552" className="edge-note">Invalid / abstain / review pending</text>
        {box('stop',650,557,250,'Explicit non-training outcome',['Reject · abstain · pending L2','No silent label promotion'])}
        {box('future',920,656,260,'Controlled SARA GCN',['Separate admission + execution','No result in public snapshot'])}
        <text x="20" y="726" className="lane-note">Solid path: historical protocol. Dashed path: extension / conditional dependency.</text>
        <text x="20" y="748" className="lane-note">This map is not a live run trace. No private verifier judgments are displayed.</text>
      </svg>
    </div>
    <figcaption><strong>Selected: {active==='input'?'Cora + text':active}</strong><p aria-live="polite">{explanations[active]}</p><button className="text-button" onClick={onAgents}>Inspect SARA roles and node evidence</button></figcaption>
    <details className="method-text-alternative"><summary>Read the flow as text</summary><ol><li>Cora and fixed FeatProp targets.</li><li>Compare B1 target text with Narrative target text plus recorded local evidence.</li><li>Parse and vote separately; apply each PS/noPS and CE/WCE condition; inspect matched saved GCN results.</li><li>Separately route frozen pairs for SARA review; run blind verification and L1 checks.</li><li>Invalid evidence or abstention stops comparison. Other protocols may require L2 first or prohibit comparison.</li><li>Permitted comparison feeds conservative arbitration. Proposals require separate admission before controlled GCN training.</li></ol></details>
  </figure>;
}
