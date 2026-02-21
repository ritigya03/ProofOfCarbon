import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Play, Brain, Satellite, BarChart3, SearchCheck, ShieldCheck, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

const agentSteps = [
  { icon: Brain, name: "Project Analysis Agent", duration: 1500 },
  { icon: Satellite, name: "Satellite Evidence Agent", duration: 1200 },
  { icon: BarChart3, name: "Baseline Agent", duration: 1000 },
  { icon: SearchCheck, name: "Fraud Reasoning Agent", duration: 1800 },
  { icon: ShieldCheck, name: "Verifier Agent", duration: 800 },
];

const Verify = () => {
  const [report, setReport] = useState("");
  const [running, setRunning] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(-1);
  const [done, setDone] = useState(false);

  const runVerification = async () => {
    if (!report.trim()) return;
    setRunning(true);
    setDone(false);
    for (let i = 0; i < agentSteps.length; i++) {
      setCurrentAgent(i);
      await new Promise((r) => setTimeout(r, agentSteps[i].duration));
    }
    setCurrentAgent(agentSteps.length);
    setDone(true);
    setRunning(false);
  };

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
            Paste or upload your carbon project report below. Our multi-agent system will analyze it and produce a trust score.
          </p>

          <div className="mt-8">
            <textarea
              value={report}
              onChange={(e) => setReport(e.target.value)}
              placeholder="Paste your carbon project report here... (e.g., project methodology, claimed emissions reductions, monitoring data)"
              className="w-full min-h-[200px] rounded-xl border border-border bg-card p-5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-y"
              disabled={running}
            />
            <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
              <Upload className="h-4 w-4" />
              <span>Or drag and drop a PDF report (demo: paste text above)</span>
            </div>
          </div>

          <button
            onClick={runVerification}
            disabled={running || !report.trim()}
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-accent-foreground transition-all hover:brightness-110 glow-orange disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Play className="h-4 w-4" />
            {running ? "Running Verification..." : "Run Verification"}
          </button>

          {/* Agent Progress */}
          <AnimatePresence>
            {(running || done) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-10 space-y-3"
              >
                {agentSteps.map((agent, i) => (
                  <motion.div
                    key={agent.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className={`flex items-center gap-4 rounded-lg border p-4 transition-all ${
                      currentAgent > i
                        ? "border-trust-green-glow/30 bg-primary/5"
                        : currentAgent === i
                        ? "border-accent/40 bg-accent/5"
                        : "border-border bg-card"
                    }`}
                  >
                    <agent.icon
                      className={`h-5 w-5 ${
                        currentAgent > i
                          ? "text-trust-green-glow"
                          : currentAgent === i
                          ? "text-accent animate-pulse"
                          : "text-muted-foreground"
                      }`}
                    />
                    <span className="text-sm font-medium">{agent.name}</span>
                    <span className="ml-auto">
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

          {done && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-8 rounded-xl border border-trust-green-glow/30 bg-primary/5 p-6 text-center"
            >
              <ShieldCheck className="mx-auto h-10 w-10 text-trust-green-glow" />
              <h3 className="mt-3 text-lg font-bold">Verification Complete</h3>
              <p className="mt-1 text-sm text-muted-foreground">All agents have finished processing.</p>
              <Link
                to="/results"
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-accent-foreground transition-all hover:brightness-110"
              >
                View Results →
              </Link>
            </motion.div>
          )}
        </motion.div>
      </div>
      <Footer />
    </main>
  );
};

export default Verify;
