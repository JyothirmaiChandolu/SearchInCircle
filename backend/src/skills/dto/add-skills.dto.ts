import { z } from 'zod';

export const addSkillsSchema = z.object({
  skills: z.array(z.string().trim().min(1).max(60)).min(1).max(50),
});

export type AddSkillsDto = z.infer<typeof addSkillsSchema>;
