import { z } from 'zod';

export const createTagSchema = z.object({
  personId: z.string().uuid().optional(),
  name: z.string().trim().min(1).max(80),
  phone: z.string().trim().min(5).optional(),
  email: z.string().trim().toLowerCase().email().optional(),
  country: z.string().trim().max(60).optional(),
  nickname: z.string().trim().max(60).optional(),
  description: z.string().trim().max(1000).optional(),
  skills: z.array(z.string().trim().min(1).max(60)).max(50).default([]),
  tools: z.array(z.string().trim().min(1).max(60)).max(50).default([]),
  yearsExperience: z.number().int().min(0).max(80).optional(),
  certifications: z.array(z.string().trim().min(1).max(100)).max(30).default([]),
  isOpen: z.boolean().default(true),
});

export type CreateTagDto = z.infer<typeof createTagSchema>;

export const updateTagSchema = createTagSchema
  .omit({ personId: true, name: true, phone: true, email: true, country: true })
  .partial();

export type UpdateTagDto = z.infer<typeof updateTagSchema>;
