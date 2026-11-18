import {
  BadRequestException,
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Post,
  Req,
  UploadedFile,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import type { Request } from 'express';
import { CognitoAuthGuard } from '../auth/cognito-auth.guard.js';
import { ResumeService } from '../resume/resume.service.js';
import { addSkillsSchema } from './dto/add-skills.dto.js';
import { SkillsService } from './skills.service.js';

@Controller('skills')
@UseGuards(CognitoAuthGuard)
export class SkillsController {
  constructor(
    private readonly skillsService: SkillsService,
    private readonly resumeService: ResumeService,
  ) {}

  @Get('me')
  me(@Req() request: Request) {
    return this.skillsService.findMine(request.user!.sub);
  }

  @Post()
  async add(@Req() request: Request, @Body() body: unknown) {
    const result = addSkillsSchema.safeParse(body);
    if (!result.success) {
      throw new BadRequestException(result.error.issues.map((i) => i.message).join(', '));
    }
    return this.skillsService.addMany(request.user!.sub, result.data.skills);
  }

  @Delete(':id')
  remove(@Req() request: Request, @Param('id') id: string) {
    return this.skillsService.remove(request.user!.sub, id);
  }

  /** Resume → suggested skills. Nothing is saved here — the caller reviews and edits
   * before POSTing the ones they want via `POST /skills`. */
  @Post('resume')
  @UseInterceptors(FileInterceptor('resume'))
  async suggestFromResume(@UploadedFile() file?: Express.Multer.File) {
    if (!file) {
      throw new BadRequestException('No resume file was received.');
    }
    const suggestions = await this.resumeService.suggestSkills(file);
    return { suggestions };
  }
}
