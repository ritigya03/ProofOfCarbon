import { motion } from "framer-motion";
import { Bot, Lock, Link as LinkIcon, Layers, Database, Shield } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

const layers = [
  {
    icon: Bot,
    title: "Agentic AI Layer",
    color: "text-trust-green-glow",
    bg: "bg-primary/10",
    items: [
      "Multi-agent orchestration with specialized roles",
      "Project Analysis, Satellite Evidence, Baseline, Fraud Reasoning, and Verifier agents",
      "LLM-powered reasoning with structured output schemas",
      "Consensus-based trust score computation",
    ],
  },
  {
    icon: Lock,
    title: "Federated Learning Layer",
    color: "text-highlight-orange",
    bg: "bg-accent/10",
    items: [
      "Privacy-preserving model training across organizations",
      "Fraud pattern detection without exposing proprietary data",
      "Differential privacy guarantees for sensitive datasets",
      "Continuously improving detection with decentralized intelligence",
    ],
  },
  {
    icon: LinkIcon,
    title: "Blockchain Audit Layer",
    color: "text-accent",
    bg: "bg-accent/10",
    items: [
      "Verification proofs anchored on Polygon Amoy testnet",
      "Immutable, timestamped, and publicly verifiable records",
      "Smart contract-based proof storage and retrieval",
      "Tamper-proof audit trail for all stakeholders",
    ],
  },
];

const Architecture = () => (
  <main className="min-h-screen">
    <Navbar />
    <div className="container mx-auto px-6 pt-28 pb-20">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto max-w-4xl"
      >
        <h1 className="text-3xl font-bold md:text-4xl">
          System <span className="text-gradient-green">Architecture</span>
        </h1>
        <p className="mt-3 text-muted-foreground max-w-2xl">
          ProofOfCarbon is built on a three-layer architecture designed for transparency, 
          privacy, and immutability — ensuring every verification is trustworthy.
        </p>

        {/* Architecture Diagram */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-12 rounded-xl border border-border bg-gradient-card p-8"
        >
          <div className="flex items-center gap-3 mb-6">
            <Layers className="h-5 w-5 text-accent" />
            <h3 className="font-semibold">System Overview</h3>
          </div>
          
          <div className="flex flex-col items-center gap-3">
            {/* User */}
            <div className="rounded-lg border border-border bg-secondary/50 px-6 py-3 text-sm font-medium">
              User / Carbon Project Report
            </div>
            <span className="text-muted-foreground/50 text-lg">↓</span>
            
            {/* AI Layer */}
            <div className="w-full rounded-lg border border-primary/30 bg-primary/5 px-6 py-4">
              <div className="flex items-center gap-2 mb-2">
                <Bot className="h-4 w-4 text-trust-green-glow" />
                <span className="text-sm font-semibold">Agentic AI Layer</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {["Analysis", "Satellite", "Baseline", "Fraud", "Verifier"].map((a) => (
                  <span key={a} className="rounded-md bg-primary/15 px-3 py-1 text-xs text-trust-green-glow">{a}</span>
                ))}
              </div>
            </div>
            <span className="text-muted-foreground/50 text-lg">↓</span>

            {/* Federated */}
            <div className="w-full rounded-lg border border-accent/30 bg-accent/5 px-6 py-4">
              <div className="flex items-center gap-2 mb-2">
                <Lock className="h-4 w-4 text-highlight-orange" />
                <span className="text-sm font-semibold">Federated Learning Layer</span>
              </div>
              <span className="text-xs text-muted-foreground">Cross-org fraud intelligence • Differential privacy • Decentralized model updates</span>
            </div>
            <span className="text-muted-foreground/50 text-lg">↓</span>

            {/* Blockchain */}
            <div className="w-full rounded-lg border border-accent/30 bg-accent/5 px-6 py-4">
              <div className="flex items-center gap-2 mb-2">
                <LinkIcon className="h-4 w-4 text-accent" />
                <span className="text-sm font-semibold">Blockchain Audit Layer</span>
              </div>
              <span className="text-xs text-muted-foreground">Polygon Amoy • Immutable proofs • Public verification • Smart contracts</span>
            </div>
            <span className="text-muted-foreground/50 text-lg">↓</span>

            {/* Output */}
            <div className="flex gap-3 flex-wrap justify-center">
              <div className="rounded-lg border border-border bg-secondary/50 px-4 py-2 text-xs font-medium flex items-center gap-2">
                <Shield className="h-3.5 w-3.5 text-trust-green-glow" /> Trust Score
              </div>
              <div className="rounded-lg border border-border bg-secondary/50 px-4 py-2 text-xs font-medium flex items-center gap-2">
                <Database className="h-3.5 w-3.5 text-accent" /> On-Chain Proof
              </div>
            </div>
          </div>
        </motion.div>

        {/* Layer Details */}
        <div className="mt-12 space-y-6">
          {layers.map((layer, i) => (
            <motion.div
              key={layer.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="rounded-xl border border-border bg-gradient-card p-8"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className={`rounded-lg ${layer.bg} p-2.5`}>
                  <layer.icon className={`h-5 w-5 ${layer.color}`} />
                </div>
                <h3 className="text-lg font-semibold">{layer.title}</h3>
              </div>
              <ul className="space-y-2">
                {layer.items.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-muted-foreground/50 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
    <Footer />
  </main>
);

export default Architecture;
