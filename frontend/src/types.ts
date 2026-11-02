export type Skill = { id: string; label: string; prerequisites: string[] };
export type Snapshot = {
  skills: Record<
    string,
    {
      mastery: number;
      attempts: number;
      errors: { type: string }[];
      response_ms: number;
      hints: number;
    }
  >;
  streak: number;
  badges: number;
  events: {
    skill: string;
    correct: boolean | null;
    error: string | null;
    hints: number;
  }[];
};
export type Task = {
  attempt_id: string;
  exercise: {
    id: string;
    skill: string;
    type: string;
    prompt: string;
    options: string[];
  };
  predicted_success: number | null;
  reason: string;
};

export type Api = (
  path: string,
  method?: string,
  body?: unknown,
  credential?: string,
) => Promise<any>;
export type RunAction = (action: () => Promise<void>) => Promise<void>;
