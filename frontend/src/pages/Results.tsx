import { motion } from "framer-motion";
import { ExternalLink, ShieldCheck, AlertTriangle, Brain, Satellite, BarChart3, SearchCheck } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import { useState } from "react";

const trustScore = 82;
const riskLevel = "Medium";

const agentOutputs = [
  {
    icon: Brain,
    name: "Project Analysis Agent",
    summary: "Project documentation is well-structured. Methodology aligns with Verra VCS standards. Claims reference verifiable data sources.",
    score: 88,
  },
  {
    icon: Satellite,
    name: "Satellite Evidence Agent",
    summary: "NDVI analysis shows moderate forest cover increase consistent with claims. Some boundary discrepancies detected in south-east quadrant.",
    score: 75,
  },
  {
    icon: BarChart3,
    name: "Baseline Agent",
    summary: "Baseline emissions calculations are within expected range. Additionality argument is moderately strong. Historical land-use data supports claims.",
    score: 84,
  },
  {
    icon: SearchCheck,
    name: "Fraud Reasoning Agent",
    summary: "No double-counting indicators found. Minor concern: monitoring frequency below industry best practices. No data manipulation signatures detected.",
    score: 79,
  },
];

const TrustGauge = ({ score }: { score: number }) => {
  const radius = 80;
  const circumference = Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="200" height="120" viewBox="0 0 200 120">
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="hsl(220, 12%, 16%)"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <motion.path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="url(#gaugeGradient)"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
        <defs>
          <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="hsl(18, 82%, 34%)" />
            <stop offset="50%" stopColor="hsl(18, 90%, 59%)" />
            <stop offset="100%" stopColor="hsl(116, 50%, 35%)" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute bottom-0 text-center">
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="text-4xl font-bold"
        >
          {score}
        </motion.span>
        <span className="text-sm text-muted-foreground">/100</span>
      </div>
    </div>
  );
};

const Results = () => {
  const [expandedAgent, setExpandedAgent] = useState<number | null>(null);

  return (
    <main className="min-h-screen">
      <Navbar />
      <div className="container mx-auto px-6 pt-28 pb-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-auto max-w-4xl"
        >
          <h1 className="text-3xl font-bold md:text-4xl">
            Verification <span className="text-gradient-green">Results</span>
          </h1>

          {/* Score + Risk */}
          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <div className="rounded-xl border border-border bg-gradient-card p-8 text-center">
              <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4">Trust Score</h3>
              <TrustGauge score={trustScore} />
            </div>
            <div className="rounded-xl border border-border bg-gradient-card p-8 flex flex-col items-center justify-center">
              <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4">Risk Level</h3>
              <span className="inline-flex items-center gap-2 rounded-full bg-accent/15 px-5 py-2 text-lg font-bold text-highlight-orange">
                <AlertTriangle className="h-5 w-5" />
                {riskLevel}
              </span>
              <p className="mt-3 text-xs text-muted-foreground">Based on multi-agent consensus</p>
            </div>
          </div>

          {/* Agent Outputs */}
          <div className="mt-10 space-y-3">
            <h3 className="text-lg font-semibold mb-4">Agent Reports</h3>
            {agentOutputs.map((agent, i) => (
              <motion.div
                key={agent.name}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <button
                  onClick={() => setExpandedAgent(expandedAgent === i ? null : i)}
                  className="w-full rounded-xl border border-border bg-gradient-card p-5 text-left transition-all hover:border-glow-green"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <agent.icon className="h-5 w-5 text-trust-green-glow" />
                      <span className="font-medium text-sm">{agent.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-trust-green-glow">{agent.score}/100</span>
                      <span className="text-muted-foreground text-xs">{expandedAgent === i ? "▲" : "▼"}</span>
                    </div>
                  </div>
                  {expandedAgent === i && (
                    <motion.p
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="mt-4 text-sm text-muted-foreground leading-relaxed border-t border-border pt-4"
                    >
                      {agent.summary}
                    </motion.p>
                  )}
                </button>
              </motion.div>
            ))}
          </div>

          {/* Blockchain Proof */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-10 rounded-xl border border-border bg-gradient-card p-8"
          >
            <div className="flex items-center gap-3 mb-4">
              <ShieldCheck className="h-6 w-6 text-trust-green-glow" />
              <h3 className="text-lg font-semibold">Blockchain Proof</h3>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground min-w-[120px]">Transaction Hash</span>
                <code className="font-mono text-xs text-foreground bg-secondary/50 px-3 py-1.5 rounded break-all">
                  0x7f3a8b...e4d2c1a9f6b8
                </code>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground min-w-[120px]">Network</span>
                <span className="text-foreground">Polygon Amoy Testnet</span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground min-w-[120px]">Status</span>
                <span className="inline-flex items-center gap-1 text-trust-green-glow">
                  <span className="h-2 w-2 rounded-full bg-trust-green-glow" />
                  Confirmed
                </span>
              </div>
            </div>
            <a
              href="https://amoy.polygonscan.com"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-5 inline-flex items-center gap-2 text-sm text-accent hover:underline"
            >
              View on Explorer <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </motion.div>
        </motion.div>
      </div>
      <Footer />
    </main>
  );
};

export default Results;
