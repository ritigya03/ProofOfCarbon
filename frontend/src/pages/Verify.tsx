import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, Play, Brain, Satellite, BarChart3, SearchCheck,
  ShieldCheck, CheckCircle2, ChevronDown, ChevronUp, FileText, X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

const agentSteps = [
  { icon: Brain,        name: "Project Analysis Agent",  duration: 2000 },
  { icon: Satellite,    name: "Satellite Evidence Agent", duration: 1800 },
  { icon: BarChart3,    name: "Baseline Agent",           duration: 1500 },
  { icon: SearchCheck,  name: "Fraud Reasoning Agent",    duration: 2200 },
  { icon: ShieldCheck,  name: "Verifier Agent",           duration: 1000 },
];

const API_URL = "http://localhost:8000";

// ── Collapsible section wrapper ──────────────────────────────────────────────
const CollapsibleSection = ({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-5 py-4 text-sm font-medium text-foreground hover:bg-secondary/30 transition-colors"
      >
        <span>{title} <span className="ml-2 text-xs text-muted-foreground font-normal">(optional)</span></span>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-5 py-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ── Reusable controlled field components ─────────────────────────────────────
const inputCls = "rounded-lg border border-border bg-secondary/30 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50";

const Field = ({ label, id, placeholder, type = "text", value, onChange, disabled }: {
  label: string; id: string; placeholder?: string; type?: string;
  value: string; onChange: (v: string) => void; disabled?: boolean;
}) => (
  <div className="flex flex-col gap-1.5">
    <label htmlFor={id} className="text-xs text-muted-foreground font-medium">{label}</label>
    <input id={id} type={type} placeholder={placeholder} value={value}
      onChange={(e) => onChange(e.target.value)} disabled={disabled} className={inputCls} />
  </div>
);

const SelectField = ({ label, id, options, value, onChange, disabled }: {
  label: string; id: string; options: string[];
  value: string; onChange: (v: string) => void; disabled?: boolean;
}) => (
  <div className="flex flex-col gap-1.5">
    <label htmlFor={id} className="text-xs text-muted-foreground font-medium">{label}</label>
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)}
      disabled={disabled} className={inputCls}>
      <option value="">Select...</option>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  </div>
);

// ── Main page ────────────────────────────────────────────────────────────────
const Verify = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [kmzFile, setKmzFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [running, setRunning] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(-1);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // ── Optional metadata fields (controlled) ──
  const [projectName, setProjectName]     = useState("");
  const [country, setCountry]             = useState("");
  const [projectType, setProjectType]     = useState("");
  const [startYear, setStartYear]         = useState("");
  const [endYear, setEndYear]             = useState("");
  const [claimedAreaHa, setClaimedAreaHa] = useState("");
  const [co2Tons, setCo2Tons]             = useState("");
  const [baselinePeriod, setBaselinePeriod] = useState("");
  const [govtMandate, setGovtMandate]     = useState("");
  const [priorReg, setPriorReg]           = useState("");

  const handleFile = (file: File | undefined | null) => {
    if (!file) return;
    if (!file.name.endsWith(".kmz")) {
      setError("Only .kmz files are accepted.");
      return;
    }
    setError(null);
    setKmzFile(file);
  };

  const runVerification = async () => {
    if (!kmzFile || !description.trim()) return;
    setRunning(true);
    setDone(false);
    setError(null);
    setCurrentAgent(0);

    // Animate agent steps while the real API call runs in parallel
    const animateAgents = async () => {
      for (let i = 0; i < agentSteps.length; i++) {
        setCurrentAgent(i);
        await new Promise((r) => setTimeout(r, agentSteps[i].duration));
      }
    };

    const callApi = async () => {
      // Build enriched claim string from optional fields
      const extras = [
        projectName   && `Project: ${projectName}`,
        country       && `Country: ${country}`,
        projectType   && `Type: ${projectType}`,
        (startYear || endYear) && `Period: ${startYear}–${endYear}`,
        claimedAreaHa && `Claimed area: ${claimedAreaHa} ha`,
        co2Tons       && `Claimed CO₂ reduction: ${co2Tons} tons/year`,
        baselinePeriod && `Baseline period: ${baselinePeriod}`,
        govtMandate   && `Government mandate: ${govtMandate}`,
        priorReg      && `Prior registration: ${priorReg}`,
      ].filter(Boolean).join(" | ");

      const fullClaim = description.trim() + (extras ? ` | ${extras}` : "");

      const form = new FormData();
      form.append("kmz_file", kmzFile, kmzFile.name);
      form.append("company_claim", fullClaim);
      const res = await fetch(`${API_URL}/analyze`, { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      return res.json();
    };

    try {
      const [result] = await Promise.all([callApi(), animateAgents()]);
      setCurrentAgent(agentSteps.length);
      setDone(true);
      setRunning(false);
      // Small pause so user sees the "done" state, then navigate
      setTimeout(() => navigate("/results", { state: { result } }), 1200);
    } catch (err: unknown) {
      setRunning(false);
      setCurrentAgent(-1);
      setError(err instanceof Error ? err.message : "Verification failed. Check the server is running.");
    }
  };

  const canSubmit = !!kmzFile && description.trim().length > 0 && !running;

  return (
    <main className="min-h-screen">
      <Navbar />
      <div className="container mx-auto px-6 pt-28 pb-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-auto max-w-3xl"
        >
          <h1 className="text-3xl font-bold md:text-4xl">
            Verify a <span className="text-gradient-green">Carbon Project</span>
          </h1>
          <p className="mt-3 text-muted-foreground">
            Upload your KMZ boundary file and describe the project. Our multi-agent system will analyze it and produce a trust score.
          </p>

          <div className="mt-10 space-y-5">

            {/* ── KMZ Upload ─────────────────────────────────────────────── */}
            <div>
              <label className="mb-2 block text-sm font-medium">
                KMZ File <span className="text-red-400">*</span>
              </label>
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  handleFile(e.dataTransfer.files[0]);
                }}
                onClick={() => !running && fileInputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 transition-all ${
                  dragOver
                    ? "border-trust-green-glow bg-primary/10"
                    : kmzFile
                    ? "border-trust-green-glow/50 bg-primary/5"
                    : "border-border bg-card hover:border-muted-foreground/40"
                } ${running ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                {kmzFile ? (
                  <>
                    <FileText className="h-8 w-8 text-trust-green-glow" />
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium">{kmzFile.name}</span>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); setKmzFile(null); }}
                        disabled={running}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {(kmzFile.size / 1024).toFixed(1)} KB
                    </span>
                  </>
                ) : (
                  <>
                    <Upload className="h-8 w-8 text-muted-foreground" />
                    <div className="text-center">
                      <p className="text-sm font-medium">Drop your .kmz file here</p>
                      <p className="mt-1 text-xs text-muted-foreground">or click to browse</p>
                    </div>
                  </>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".kmz"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0])}
              />
            </div>

            {/* ── Project Description ─────────────────────────────────────── */}
            <div>
              <label htmlFor="description" className="mb-2 block text-sm font-medium">
                Project Description <span className="text-red-400">*</span>
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. GreenFuture Ltd — 500 ha forest conservation in Kodagu, Karnataka. Dense evergreen forest, carbon sequestration project since 2020."
                rows={5}
                disabled={running}
                className="w-full rounded-xl border border-border bg-card px-5 py-4 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-ring resize-y disabled:opacity-50"
              />
            </div>

            {/* ── Collapsible: Additional Metadata ───────────────────────── */}
            <CollapsibleSection title="Additional Metadata">
              <Field id="project_name" label="Project Name" placeholder="e.g. Kodagu Reforestation"
                value={projectName} onChange={setProjectName} disabled={running} />
              <Field id="country" label="Country" placeholder="e.g. India"
                value={country} onChange={setCountry} disabled={running} />
              <SelectField id="project_type" label="Project Type"
                value={projectType} onChange={setProjectType} disabled={running}
                options={["REDD+", "Afforestation", "Reforestation", "Improved Forest Management", "Agroforestry", "Blue Carbon", "Other"]} />
              <div className="flex gap-3">
                <Field id="start_year" label="Start Year" type="number" placeholder="2020"
                  value={startYear} onChange={setStartYear} disabled={running} />
                <Field id="end_year" label="End Year" type="number" placeholder="2030"
                  value={endYear} onChange={setEndYear} disabled={running} />
              </div>
            </CollapsibleSection>

            {/* ── Collapsible: Claimed Impact ─────────────────────────────── */}
            <CollapsibleSection title="Claimed Impact">
              <Field id="claimed_area_ha" label="Claimed Area (ha)" type="number" placeholder="e.g. 500"
                value={claimedAreaHa} onChange={setClaimedAreaHa} disabled={running} />
              <Field id="co2_tons" label="Claimed CO₂ Reduction (tons/year)" type="number" placeholder="e.g. 12000"
                value={co2Tons} onChange={setCo2Tons} disabled={running} />
            </CollapsibleSection>

            {/* ── Collapsible: Baseline & Context ────────────────────────── */}
            <CollapsibleSection title="Baseline & Context">
              <Field id="baseline_period" label="Baseline Period" placeholder="e.g. 2010–2019"
                value={baselinePeriod} onChange={setBaselinePeriod} disabled={running} />
              <SelectField id="govt_mandate" label="Government Mandate?"
                value={govtMandate} onChange={setGovtMandate} disabled={running}
                options={["Yes", "No", "Partial"]} />
              <SelectField id="prior_registration" label="Prior Registration?"
                value={priorReg} onChange={setPriorReg} disabled={running}
                options={["None", "Verra VCS", "Gold Standard", "CDM", "India BEE PAT", "Other"]} />
            </CollapsibleSection>

            {/* ── Error ───────────────────────────────────────────────────── */}
            {error && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                ❌ {error}
              </div>
            )}

            {/* ── Submit ──────────────────────────────────────────────────── */}
            <button
              type="button"
              onClick={runVerification}
              disabled={!canSubmit}
              className="inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-accent-foreground transition-all hover:brightness-110 glow-orange disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Play className="h-4 w-4" />
              {running ? "Running Verification..." : "Run Verification"}
            </button>
          </div>

          {/* ── Agent Progress ─────────────────────────────────────────────── */}
          <AnimatePresence>
            {(running || done) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-10 space-y-3"
              >
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
                  Agent Pipeline
                </h3>
                {agentSteps.map((agent, i) => (
                  <motion.div
                    key={agent.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.08 }}
                    className={`flex items-center gap-4 rounded-lg border p-4 transition-all ${
                      currentAgent > i
                        ? "border-trust-green-glow/30 bg-primary/5"
                        : currentAgent === i
                        ? "border-accent/40 bg-accent/5"
                        : "border-border bg-card"
                    }`}
                  >
                    <agent.icon
                      className={`h-5 w-5 shrink-0 ${
                        currentAgent > i
                          ? "text-trust-green-glow"
                          : currentAgent === i
                          ? "text-accent animate-pulse"
                          : "text-muted-foreground"
                      }`}
                    />
                    <span className="text-sm font-medium">{agent.name}</span>
                    <span className="ml-auto shrink-0">
                      {currentAgent > i ? (
                        <CheckCircle2 className="h-4 w-4 text-trust-green-glow" />
                      ) : currentAgent === i ? (
                        <span className="text-xs text-accent">Processing...</span>
                      ) : (
                        <span className="text-xs text-muted-foreground">Pending</span>
                      )}
                    </span>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

        </motion.div>
      </div>
      <Footer />
    </main>
  );
};

export default Verify;
