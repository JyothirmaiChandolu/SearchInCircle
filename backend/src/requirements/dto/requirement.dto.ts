import { z } from 'zod';

export const createRequirementSchema = z
  .object({
    title: z.string().trim().min(1).max(120),
    description: z.string().trim().min(1).max(2000),
    skillsNeeded: z.array(z.string().trim().min(1).max(60)).max(30).default([]),
    workType: z.enum(['REMOTE', 'ON_SITE']),
    experienceRequired: z.string().trim().max(60).optional(),
    salary: z.string().trim().max(60).optional(),
    location: z.string().trim().max(120).optional(),
  })
  .refine((v) => v.workType === 'REMOTE' || !!v.location, {
    message: 'Location is required for on-site requirements.',
    path: ['location'],
  });

export type CreateRequirementDto = z.infer<typeof createRequirementSchema>;

export const updateRequirementSchema = z.object({
  title: z.string().trim().min(1).max(120).optional(),
  description: z.string().trim().min(1).max(2000).optional(),
  skillsNeeded: z.array(z.string().trim().min(1).max(60)).max(30).optional(),
  workType: z.enum(['REMOTE', 'ON_SITE']).optional(),
  experienceRequired: z.string().trim().max(60).optional(),
  salary: z.string().trim().max(60).optional(),
  location: z.string().trim().max(120).optional(),
  isOpen: z.boolean().optional(),
});

export type UpdateRequirementDto = z.infer<typeof updateRequirementSchema>;
