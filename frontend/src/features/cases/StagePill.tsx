import type { CaseStage } from "@/api/types";
import { Pill } from "@/components/ui/Pill";
import { STAGE_LABEL, STAGE_TONE } from "./stages";

export function StagePill({ stage }: { stage: CaseStage }) {
  return <Pill tone={STAGE_TONE[stage]}>{STAGE_LABEL[stage]}</Pill>;
}
