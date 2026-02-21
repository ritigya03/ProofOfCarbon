import { motion } from "framer-motion";
import { Upload, Cpu, Gauge, Link as LinkIcon } from "lucide-react";

const steps = [
  { icon: Upload, label: "Upload", desc: "Submit carbon project report or documentation" },
  { icon: Cpu, label: "Analyze", desc: "Multi-agent AI processes and cross-validates claims" },
  { icon: Gauge, label: "Score", desc: "Trust score and risk level computed from agent consensus" },
  { icon: LinkIcon, label: "On-Chain Proof", desc: "Verification hash anchored immutably on blockchain" },
];

const WorkflowSection = () => (
  <section className="section-padding">
    <div className="container mx-auto px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="text-center"
      >
        <h2 className="text-3xl font-bold md:text-4xl">
          How It <span className="text-gradient-orange">Works</span>
        </h2>
      </motion.div>

      <div className="mt-16 flex flex-col md:flex-row items-start justify-center gap-4">
        {steps.map((step, i) => (
          <div key={step.label} className="flex flex-col md:flex-row items-center gap-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.15 }}
              className="flex flex-col items-center text-center w-44"
            >
              <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-full border border-border bg-gradient-card">
                <step.icon className="h-7 w-7 text-accent" />
              </div>
              <h4 className="text-sm font-bold">{step.label}</h4>
              <p className="mt-1 text-xs text-muted-foreground">{step.desc}</p>
            </motion.div>
            {i < steps.length - 1 && (
              <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15 + 0.3 }}
                className="hidden md:block text-muted-foreground/40 text-2xl"
              >
                →
              </motion.div>
            )}
          </div>
        ))}
      </div>
    </div>
  </section>
);

export default WorkflowSection;
