import type { Database, ImageStore } from "./storage.js";
import { z } from "zod";
export const languages: Record<string, string> = {
  en: "English",
  zh: "中文",
  es: "Español",
  hi: "हिन्दी",
  ar: "العربية",
  pt: "Português",
  ru: "Русский",
  ja: "日本語",
  de: "Deutsch",
  fr: "Français",
};
export const dishSchema = z
  .object({
    name_original: z.string().trim().min(1).max(200),
    name_translated: z.string().trim().min(1).max(200),
    description_original: z.string().max(1200),
    description_translated: z.string().max(1200),
    price: z.string().max(100),
    category: z.string().min(1).max(100),
    course: z.enum(["starter", "main", "dessert", "drink", "other"]),
  })
  .strict();
export const menuSchema = z
  .object({
    title: z.string().min(1).max(160),
    source_language: z.string().max(80),
    warnings: z.array(z.string().max(500)).max(10),
    dishes: z.array(dishSchema).max(100),
  })
  .strict();
export type Provider = "muse" | "openai";
export type ImageState = {
  status: "starting" | "pending" | "ready" | "failed" | "uncertain";
  error: string;
  attempts: number;
  url?: string;
};
export type Dish = z.infer<typeof dishSchema> & {
  id: string;
  image?: ImageState | null;
};
export type Menu = Omit<z.infer<typeof menuSchema>, "dishes"> & {
  id: string;
  language: string;
  created_at: number;
  dishes: Dish[];
  demo?: boolean;
};
export interface Env {
  DB: Database;
  IMAGES: ImageStore;
  ASSETS: { fetch(request: Request): Promise<Response> };
  request?: typeof fetch;
  AI_PROVIDER?: string;
  MODEL_API_KEY?: string;
  OPENAI_API_KEY?: string;
  MUSE_MENU_MODEL?: string;
  MUSE_IMAGE_MODEL?: string;
  OPENAI_MENU_MODEL?: string;
  OPENAI_IMAGE_MODEL?: string;
  DAILY_SCAN_LIMIT?: string;
  DAILY_IMAGE_LIMIT?: string;
  HOURLY_SCAN_LIMIT?: string;
  HOURLY_IMAGE_LIMIT?: string;
}
export class AppError extends Error {
  constructor(
    public status: number,
    message: string,
    public uncertain = false,
  ) {
    super(message);
  }
}
export function provider(env: Env): Provider {
  const p = env.AI_PROVIDER ?? "muse";
  if (p !== "muse" && p !== "openai")
    throw new AppError(503, "The AI provider setting is invalid.");
  return p;
}
