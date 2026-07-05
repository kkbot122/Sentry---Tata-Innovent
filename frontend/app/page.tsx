"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIcon,
  BellRinging,
  ChartLineUp,
  Gauge,
  Pulse,
  Radio,
  ShieldCheck,
  WarningDiamond,
} from "@phosphor-icons/react";
import {
  Area,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

type HealthState = "Healthy" | "Warning" | "Critical" | "Waiting";

type FeatureDeviation = {
  feature: string;
  value: number;
  baseline_mean: number;
  baseline_std: number;
  z_score: number;
};

type DashboardPayload = {
  timestamp: string;
  replay_state: HealthState;
  prediction: HealthState;
  confidence: number;
  confidence_percent: number;
  latency_ms: number;
  top_deviation: FeatureDeviation;
  recommendation: string;
  features: Record<string, number>;
  source_file: string;
  chunk_index: number;
  signal: number[];
};

type AlertItem = {
  id: string;
  timestamp: string;
  state: HealthState;
  feature: string;
  recommendation: string;
};

type SignalPoint = {
  index: number;
  value: number;
};

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000/ws/live";

const featureLabels: Record<string, string> = {
  rms: "RMS",
  std: "Std Dev",
  kurtosis: "Kurtosis",
  dominant_freq_hz: "Dominant Hz",
  spectral_energy: "Spectral Energy",
};

const stateCopy: Record<
  HealthState,
  { label: string; dot: string; text: string; icon: typeof ShieldCheck }
> = {
  Healthy: {
    label: "Healthy",
    dot: "bg-[#6798ff]",
    text: "text-white",
    icon: ShieldCheck,
  },
  Warning: {
    label: "Warning",
    dot: "bg-[#f3c969]",
    text: "text-[#f3c969]",
    icon: WarningDiamond,
  },
  Critical: {
    label: "Critical",
    dot: "bg-[#ff6b6b]",
    text: "text-[#ff6b6b]",
    icon: WarningDiamond,
  },
  Waiting: {
    label: "Waiting",
    dot: "bg-[#7c7c7c]",
    text: "text-[#a7a7a7]",
    icon: Radio,
  },
};

function formatTime(value?: string) {
  if (!value) return "--:--:--";
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function formatNumber(value?: number, digits = 2) {
  if (value === undefined || Number.isNaN(value)) return "--";
  return value.toLocaleString("en", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function downsampleSignal(signal: number[], chunkIndex: number) {
  const stride = Math.max(1, Math.floor(signal.length / 96));
  return signal
    .filter((_, index) => index % stride === 0)
    .map((value, index) => ({
      index: chunkIndex * 100 + index,
      value,
    }));
}

export default function Home() {
  const [payload, setPayload] = useState<DashboardPayload | null>(null);
  const [connection, setConnection] = useState<
    "connecting" | "online" | "offline"
  >("connecting");
  const [signalPoints, setSignalPoints] = useState<SignalPoint[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const lastAlertState = useRef<HealthState>("Waiting");

  useEffect(() => {
    const socket = new WebSocket(WS_URL);

    socket.addEventListener("open", () => setConnection("online"));
    socket.addEventListener("close", () => setConnection("offline"));
    socket.addEventListener("error", () => setConnection("offline"));
    socket.addEventListener("message", (event) => {
      const nextPayload = JSON.parse(event.data) as DashboardPayload;
      setPayload(nextPayload);
      setSignalPoints((current) => {
        const nextPoints = downsampleSignal(
          nextPayload.signal,
          nextPayload.chunk_index,
        );
        return [...current, ...nextPoints].slice(-360);
      });

      if (
        nextPayload.prediction !== "Healthy" &&
        nextPayload.prediction !== lastAlertState.current
      ) {
        lastAlertState.current = nextPayload.prediction;
        setAlerts((current) =>
          [
            {
              id: `${nextPayload.chunk_index}-${nextPayload.prediction}`,
              timestamp: nextPayload.timestamp,
              state: nextPayload.prediction,
              feature: nextPayload.top_deviation.feature,
              recommendation: nextPayload.recommendation,
            },
            ...current,
          ].slice(0, 8),
        );
      }

      if (nextPayload.prediction === "Healthy") {
        lastAlertState.current = "Healthy";
      }
    });

    return () => socket.close();
  }, []);

  const state = payload?.prediction ?? "Waiting";
  const stateMeta = stateCopy[state];
  const StateIcon = stateMeta.icon;

  const featureRows = useMemo(() => {
    const features = payload?.features ?? {};
    return Object.entries(featureLabels).map(([key, label]) => ({
      key,
      label,
      value: features[key],
      active: payload?.top_deviation.feature === key,
    }));
  }, [payload]);

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="blueprint-grid pointer-events-none fixed inset-0 opacity-[0.18]" />

      <div className="relative mx-auto flex min-h-screen max-w-[1200px] flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-4 border-b border-[#1e1e1e] pb-5 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="font-mono text-xs uppercase tracking-[0.85px] text-[#a7a7a7]">
              Bearing Fault Edge Monitor
            </div>
            <h1 className="mt-2 text-4xl font-semibold leading-[1.2] tracking-[-0.84px] text-white">
              Live vibration control room
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={connection === "online" ? "active" : "default"}>
              <span
                className={cn(
                  "h-2 w-2 rounded-[4px]",
                  connection === "online" ? "bg-[#6798ff]" : "bg-[#7c7c7c]",
                )}
              />
              {connection}
            </Badge>
            <Button variant="outline" className="font-mono uppercase tracking-[0.85px]">
              <Radio size={18} weight="bold" />
              ws/live
            </Button>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
          <Card className="min-h-[420px] border-[#313131] bg-[#141414]">
            <CardHeader className="flex flex-row items-start justify-between gap-4">
              <div>
                <div className="font-mono text-xs uppercase tracking-[0.85px] text-[#a7a7a7]">
                  Raw sensor stream
                </div>
                <CardTitle className="mt-2">Drive-end vibration signal</CardTitle>
              </div>
              <Badge variant="active">
                <Pulse size={16} weight="bold" className="text-[#6798ff]" />
                {payload ? `chunk ${payload.chunk_index}` : "standby"}
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] rounded-[8px] border border-[#313131] bg-[#0a0a0a] p-3">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={signalPoints}>
                    <CartesianGrid stroke="#1e1e1e" vertical={false} />
                    <XAxis dataKey="index" hide />
                    <YAxis
                      width={42}
                      tick={{ fill: "#7c7c7c", fontSize: 12 }}
                      stroke="#313131"
                    />
                    <Tooltip
                      cursor={{ stroke: "#6798ff", strokeWidth: 1 }}
                      contentStyle={{
                        background: "#141414",
                        border: "1px solid #313131",
                        borderRadius: "8px",
                        color: "#ffffff",
                      }}
                      labelStyle={{ color: "#a7a7a7" }}
                    />
                    <Area dataKey="value" fill="#6798ff" fillOpacity={0.06} />
                    <Line
                      type="monotone"
                      dataKey="value"
                      dot={false}
                      stroke="#6798ff"
                      strokeWidth={1.5}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card className="border-[#313131]">
            <CardHeader>
              <div className="font-mono text-xs uppercase tracking-[0.85px] text-[#a7a7a7]">
                Current health
              </div>
              <div className="mt-4 flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-[8px] border border-[#313131] bg-[#141414]">
                  <StateIcon size={25} weight="bold" className={stateMeta.text} />
                </div>
                <div>
                  <div
                    className={cn(
                      "text-4xl font-semibold leading-[1.2] tracking-[-0.84px]",
                      stateMeta.text,
                    )}
                  >
                    {stateMeta.label}
                  </div>
                  <div className="mt-1 text-sm tracking-[-0.17px] text-[#a7a7a7]">
                    {payload?.source_file ?? "awaiting backend stream"}
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <Separator />
              <div className="grid grid-cols-2 gap-3">
                <Metric
                  icon={Gauge}
                  label="Latency"
                  value={`${formatNumber(payload?.latency_ms, 2)} ms`}
                />
                <Metric
                  icon={ChartLineUp}
                  label="Confidence"
                  value={`${formatNumber(payload?.confidence_percent, 1)}%`}
                />
              </div>
              <div>
                <div className="mb-2 font-mono text-xs uppercase tracking-[0.85px] text-[#a7a7a7]">
                  Recommendation
                </div>
                <p className="min-h-20 rounded-[8px] border border-[#313131] bg-[#141414] p-4 text-sm leading-6 tracking-[-0.17px] text-[#d4d4d4]">
                  {payload?.recommendation ?? "Waiting for edge inference output."}
                </p>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <Card className="border-[#313131]">
            <CardHeader>
              <div className="font-mono text-xs uppercase tracking-[0.85px] text-[#a7a7a7]">
                Feature vector
              </div>
              <CardTitle className="mt-2">Window diagnostics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {featureRows.map((feature) => (
                <div
                  key={feature.key}
                  className="grid grid-cols-[1fr_auto] items-center gap-4 rounded-[8px] border border-[#313131] bg-[#141414] px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <ActivityIcon
                      size={18}
                      weight="bold"
                      className={feature.active ? "text-[#6798ff]" : "text-[#a7a7a7]"}
                    />
                    <div>
                      <div className="text-sm font-medium tracking-[-0.17px] text-white">
                        {feature.label}
                      </div>
                      <div className="font-mono text-xs uppercase tracking-[0.85px] text-[#7c7c7c]">
                        {feature.active ? "top deviation" : "feature"}
                      </div>
                    </div>
                  </div>
                  <div className="font-mono text-sm tracking-[0.85px] text-[#a7a7a7]">
                    {formatNumber(feature.value, feature.key === "dominant_freq_hz" ? 1 : 3)}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-[#313131]">
            <CardHeader className="flex flex-row items-start justify-between gap-4">
              <div>
                <div className="font-mono text-xs uppercase tracking-[0.85px] text-[#a7a7a7]">
                  Alert feed
                </div>
                <CardTitle className="mt-2">State changes</CardTitle>
              </div>
              <BellRinging size={22} weight="bold" className="text-[#6798ff]" />
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {alerts.length ? (
                  alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className="grid gap-2 rounded-[8px] border border-[#313131] bg-[#141414] p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <Badge variant={alert.state.toLowerCase() as "warning" | "critical"}>
                          <span
                            className={cn(
                              "h-2 w-2 rounded-[4px]",
                              stateCopy[alert.state].dot,
                            )}
                          />
                          {alert.state}
                        </Badge>
                        <span className="font-mono text-xs tracking-[0.85px] text-[#7c7c7c]">
                          {formatTime(alert.timestamp)}
                        </span>
                      </div>
                      <div className="text-sm font-medium tracking-[-0.17px] text-white">
                        {featureLabels[alert.feature] ?? alert.feature}
                      </div>
                      <p className="text-sm leading-6 tracking-[-0.17px] text-[#a7a7a7]">
                        {alert.recommendation}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="rounded-[8px] border border-[#313131] bg-[#141414] p-6 text-sm tracking-[-0.17px] text-[#a7a7a7]">
                    No active fault transitions.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Gauge;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-[8px] border border-[#313131] bg-[#141414] p-4">
      <Icon size={18} weight="bold" className="text-[#6798ff]" />
      <div className="mt-4 text-2xl font-semibold tracking-[-0.5px] text-white">
        {value}
      </div>
      <div className="mt-1 text-sm tracking-[-0.17px] text-[#a7a7a7]">
        {label}
      </div>
    </div>
  );
}
