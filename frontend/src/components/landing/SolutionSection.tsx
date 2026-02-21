import { motion } from "framer-motion";
import { Brain, Satellite, BarChart3, SearchCheck, ShieldCheck } from "lucide-react";

const agents = [
  { icon: Brain, name: "Project Analysis Agent", desc: "Parses carbon project documents and extracts key claims, methodologies, and expected outcomes." },
  { icon: Satellite, name: "Satellite Evidence Agent", desc: "Cross-references project claims with satellite imagery and geospatial data for ground-truth validation." },
  { icon: BarChart3, name: "Baseline Agent", desc: "Compares historical baselines and emission reduction projections against industry benchmarks." },
  { icon: SearchCheck, name: "Fraud Reasoning Agent", desc: "Applies adversarial reasoning patterns to identify potential double-counting, inflated claims, or manipulated data." },
  { icon: ShieldCheck, name: "Verifier Agent", desc: "Aggregates all agent outputs, computes a trust score, and produces the final verification report." },
];

const SolutionSection = () => (
  <section className="section-padding">
    <div className="container mx-auto px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="text-center"
      >
        <h2 className="text-3xl font-bold md:text-4xl">
          Multi-Agent <span className="text-gradient-green">Verification System</span>
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
          Five specialized AI agents collaborate to produce a comprehensive, bias-resistant verification.
        </p>
      </motion.div>

      <div className="mt-16 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent, i) => (
          <motion.div
            key={agent.name}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            className="group rounded-xl border border-border bg-gradient-card p-7 transition-all hover:border-glow-green hover:glow-green"
          >
            <div className="mb-4 inline-flex rounded-lg bg-primary/15 p-3">
              <agent.icon className="h-6 w-6 text-trust-green-glow" />
            </div>
            <h3 className="text-base font-semibold">{agent.name}</h3>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{agent.desc}</p>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default SolutionSection;
