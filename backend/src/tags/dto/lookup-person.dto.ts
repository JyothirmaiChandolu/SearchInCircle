import { z } from 'zod';

export const lookupPersonSchema = z
  .object({
    phone: z.string().trim().min(5).optional(),
    email: z.string().trim().toLowerCase().email().optional(),
  })
  .refine((v) => v.phone || v.email, { message: 'Provide a phone number or email to check.' });

export type LookupPersonDto = z.infer<typeof lookupPersonSchema>;
