from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from common.models import WebResource, WebLink, PublicationJournal, Publication
from protein.models import (ProteinSegment, ProteinAnomaly, ProteinAnomalyType, ProteinAnomalyRuleSet,
    ProteinAnomalyRule)
from ligand.models import Ligand, LigandProperities, LigandType, LigandRole
from residue.models import ResidueGenericNumber, ResidueNumberingScheme
from documentation.models import Documentation
from news.models import News
from pages.models import Pages

import logging
import shlex
import os
import yaml

class Command(BaseCommand):
    help = 'Reads source data and creates common database tables'

    logger = logging.getLogger(__name__)

    resource_source_file = os.sep.join([settings.DATA_DIR, 'common_data', 'resources.txt'])
    ligands_source_file = os.sep.join([settings.DATA_DIR, 'ligand_data', 'ligands.yaml'])
    publications_source_file = os.sep.join([settings.DATA_DIR, 'publications_data', 'publications.yaml'])
    documentation_data_dir = os.sep.join([settings.DATA_DIR, 'documentation'])
    news_data_dir = os.sep.join([settings.DATA_DIR, 'news'])
    pages_data_dir = os.sep.join([settings.DATA_DIR, 'pages'])
    segment_source_file = os.sep.join([settings.DATA_DIR, 'protein_data', 'segments.txt'])
    residue_number_scheme_source_file = os.sep.join([settings.DATA_DIR, 'residue_data', 'generic_numbers',
        'schemes.txt'])
    anomaly_source_dir = os.sep.join([settings.DATA_DIR, 'structure_data', 'anomalies'])

    def handle(self, *args, **options):
        functions = [
            'create_resources',
            'create_ligands',
            'create_documentation',
            'create_news',
            'create_pages',
            'create_publications',
            'create_protein_segments',
            'create_residue_numbering_schemes',
            'create_anomalies',
        ]

        # execute functions
        for f in functions:
            try:
                getattr(self, f)()
            except Exception as msg:
                print(msg)
                self.logger.error(msg)

    def create_resources(self):
        self.logger.info('CREATING RESOURCES')
        self.logger.info('Parsing file ' + self.resource_source_file)

        with open(self.resource_source_file, "r", encoding='UTF-8') as resource_source_file:
            for row in resource_source_file:
                split_row = shlex.split(row)

                # create resource
                try:
                    defaults = {
                        'name': split_row[1],
                        'url': split_row[2]
                    }

                    wr, created = WebResource.objects.get_or_create(slug=split_row[0], defaults=defaults)

                    if created:
                        self.logger.info('Created resource ' + wr.slug)
                    
                except:
                    self.logger.error('Failed creating resource ' + split_row[0])
                    continue

        self.logger.info('COMPLETED CREATING RESOURCES')

    def create_ligands(self):
        self.logger.info('CREATING LIGANDS')
        self.logger.info('Parsing file ' + self.ligands_source_file)

        with open(self.ligands_source_file, 'r') as f:
            ls = yaml.load(f)
            for l in ls:

                try:
                    web_resource = WebResource.objects.get(slug='pubchem')
                except:
                    # abort if pdb resource is not found
                    raise Exception('PubChem resource not found, aborting!')

                if 'ligand_type__slug' in l:
                    lt, created = LigandType.objects.get_or_create(slug=l['ligand_type__slug'],name=l['ligand_type__name'])
                else:
                    lt = None

                if l['smiles']==None and l['inchikey']==None: #If they are None they need their own entry, in case the smiles get determined
                    #Test first if there exists a ligand with the properities, so duplicates are not inserted
                    if not Ligand.objects.filter(name=l['name'], canonical=l['canonical'], ambigious_alias=l['ambigious_alias'], properities__smiles=None).exists():
                        lp = LigandProperities.objects.create(smiles=l['smiles'], inchikey=l['inchikey'],ligand_type=lt)
                    else: #if no properities but ligand is already there, don't create more properities.
                        continue
                else:
                    lp, created = LigandProperities.objects.get_or_create(smiles=l['smiles'], inchikey=l['inchikey'],ligand_type=lt)

                for weblink in l['ligand__weblinks']:
                    web_resource = WebResource.objects.get(slug=weblink[1])
                    wl, created = WebLink.objects.get_or_create(index=weblink[0], web_resource=web_resource)
                    lp.web_links.add(wl)

                lig, created = Ligand.objects.get_or_create(name=l['name'], canonical=l['canonical'], ambigious_alias=l['ambigious_alias'], properities=lp)
                if created:
                    self.logger.info('Created ligand ' + l['name'])

        self.logger.info('COMPLETED CREATING LIGANDS')

    def create_documentation(self):
        self.logger.info('CREATING DOCUMENTATION')
        
        # what files should be parsed?
        filenames = os.listdir(self.documentation_data_dir)

        for source_file in filenames:
            self.logger.info('Parsing file ' + source_file)
            source_file_path = os.sep.join([self.documentation_data_dir, source_file])

            if source_file.endswith('.yaml'):
                with open(source_file_path, 'r') as f:
                    ds = yaml.load(f)

                    doc, created = Documentation.objects.get_or_create(title=ds['title'] , description=ds['description'], image=ds['image'] ,)

                    if created:
                        self.logger.info('Created documentation for ' + ds['title'])
                with open(source_file_path[:-4]+'html', 'r') as h:

                    doc.html = h.read()
                    doc.save()

                    if created:
                        self.logger.info('Created html documentation for ' + ds['title'])

        self.logger.info('COMPLETED CREATING DOCUMENTATION')

    def create_pages(self):
        self.logger.info('CREATING PAGES')
        
        # what files should be parsed?
        filenames = sorted(os.listdir(self.pages_data_dir),key=str.lower)

        for source_file in filenames:
            self.logger.info('Parsing file ' + source_file)
            source_file_path = os.sep.join([self.pages_data_dir, source_file])

            if source_file.endswith('.yaml'):
                with open(source_file_path, 'r') as f:
                    ds = yaml.load(f)

                    doc, created = Pages.objects.get_or_create(title=ds['title'])

                    if created:
                        self.logger.info('Created pages for ' + ds['title'])
                with open(source_file_path[:-4]+'html', 'r') as h:

                    doc.html = h.read()
                    doc.save()

                    if created:
                        self.logger.info('Created html pages for ' + ds['title'])

        self.logger.info('COMPLETED CREATING PAGES')

    def create_news(self):
        self.logger.info('CREATING NEWS')
        
        # what files should be parsed?
        filenames = os.listdir(self.news_data_dir)

        for source_file in filenames:
            self.logger.info('Parsing file ' + source_file)
            source_file_path = os.sep.join([self.news_data_dir, source_file])

            if source_file.endswith('.yaml'):
                with open(source_file_path, 'r') as f:
                    ds = yaml.load(f)

                    doc, created = News.objects.get_or_create(image=ds['image'], date=ds['date'])

                    if created:
                        self.logger.info('Created news for ' + ds['date'])
                with open(source_file_path[:-4]+'html', 'r') as h:

                    doc.html = h.read()
                    doc.save()

                    if created:
                        self.logger.info('Created html news for ' + ds['date'])

        self.logger.info('COMPLETED CREATING NEWS')

    def create_publications(self):
        self.logger.info('CREATING PUBLICATIONS')
        self.logger.info('Parsing file ' + self.publications_source_file)

        num_created = 0
        with open(self.publications_source_file, 'r') as f:
            ps = yaml.load(f)
            for p in ps:

                try:
                    web_resource = WebResource.objects.get(slug=p['weblink_resource'])
                except:
                    # abort if pdb resource is not found
                    raise Exception(p['weblink_resource'] + ' resource not found, aborting!')

                wl, created = WebLink.objects.get_or_create(index=p['weblink_index'], web_resource=web_resource)
                j, created = PublicationJournal.objects.get_or_create(slug=p['journal_slug'], name=p['journal_name'])
                pub, created = Publication.objects.get_or_create(title=p['title'], authors=p['authors'],
                    year=p['year'] , reference=p['reference'] , journal=j, web_link=wl)

                if created:
                    num_created += 1
        
        self.logger.info('Created {} publications'.format(str(num_created)))

        self.logger.info('COMPLETED CREATING PUBLICATIONS')

    def create_protein_segments(self):
        self.logger.info('CREATING PROTEIN SEGMENTS')
        self.logger.info('Parsing file ' + self.segment_source_file)

        with open(self.segment_source_file, "r", encoding='UTF-8') as segment_file:
            for row in segment_file:
                split_row = shlex.split(row)

                # create segment
                try:
                    defaults={
                        'category': split_row[1],
                        'name': split_row[2]
                    }

                    s, created = ProteinSegment.objects.get_or_create(slug=split_row[0], defaults=defaults)

                    if created:
                        self.logger.info('Created protein segment ' + s.name)
                except:
                    self.logger.error('Failed creating protein segment {}'.format(split(row[0])))
                    continue

        self.logger.info('COMPLETED CREATING PROTEIN SEGMENTS')

    def create_residue_numbering_schemes(self):
        self.logger.info('CREATING RESIDUE NUMBERING SCHEMES')
        self.logger.info('Parsing file ' + self.residue_number_scheme_source_file)

        with open(self.residue_number_scheme_source_file, "r", encoding='UTF-8') as residue_number_scheme_source_file:
            for row in residue_number_scheme_source_file:
                split_row = shlex.split(row)

                # create scheme
                try:
                    defaults={
                        'short_name': split_row[1],
                        'name': split_row[2]
                    }
                    if len(split_row) == 4:
                        try:
                            prns = split_row[3]
                            parent = ResidueNumberingScheme.objects.get(slug=prns)
                        except ResidueNumberingScheme.DoesNotExists:
                            raise Exception('Parent scheme {} does not exists, aborting!'.format(prns))
                        defaults['parent'] = parent

                    s, created = ResidueNumberingScheme.objects.get_or_create(slug=split_row[0], defaults=defaults)
                    
                    if created:
                        self.logger.info('Created residue numbering scheme ' + s.short_name)
                except:
                    self.logger.error('Failed creating residue numbering scheme {}'.format(split_row[0]))
                    continue

        self.logger.info('COMPLETED CREATING RESIDUE NUMBERING SCHEMES')

    def create_anomalies(self):
        self.logger.info('CREATING PROTEIN ANOMALIES')
        
        filenames = os.listdir(self.anomaly_source_dir)
        for source_file in filenames:
            source_file_path = os.sep.join([self.anomaly_source_dir, source_file])
            if os.path.isfile(source_file_path) and source_file[0] != '.':
                self.logger.info('Parsing file {}'.format(source_file_path))
                # read the yaml file
                with open(source_file_path, 'r') as f:
                    ano = yaml.load(f)

                    # anomaly type
                    if 'anomaly_type' in ano and ano['anomaly_type']:
                        at, created = ProteinAnomalyType.objects.get_or_create(slug=ano['anomaly_type'],
                            defaults={'name': ano['anomaly_type'].title()})
                        if created:
                            self.logger.info('Created protein anomaly type {}'.format(at.slug))
                    else:
                        self.logger.error('Anomaly type not specified in file {}, skipping!'.format(source_file))
                        continue

                    # protein segment
                    if 'protein_segment' in ano and ano['protein_segment']:
                        try:
                            ps = ProteinSegment.objects.get(slug=ano['protein_segment'])
                        except ProteinSegment.DoesNotExists:
                            self.logger.error('Protein segment {} not found, skipping!'.format(
                                anop['protein_segmemt']))
                            continue

                    # generic number
                    if 'generic_number' in ano and ano['generic_number']:
                        rns = ResidueNumberingScheme.objects.get(slug=settings.DEFAULT_NUMBERING_SCHEME)
                        gn, created = ResidueGenericNumber.objects.get_or_create(label=ano['generic_number'],
                            scheme=rns, defaults={'protein_segment': ps})
                        if created:
                            self.logger.info('Created generic number {}'.format(gn.label))
                    else:
                        self.logger.error('Generic number not specified in file {}, skipping!'.format(source_file))
                        continue

                    # anomaly
                    pa, created = ProteinAnomaly.objects.get_or_create(anomaly_type=at, generic_number=gn)
                    if created:
                        self.logger.info('Created {} {}'.format(at.slug, gn.label))

                    # rule sets
                    if 'rule_sets' not in ano:
                        self.logger.error('No rule sets specified in file {}, skipping!'.format(source_file))
                        continue
                    for i, rule_set in enumerate(ano['rule_sets']):
                        # exclusive rule set?
                        exclusive = False
                        if 'exclusive' in rule_set and rule_set['exclusive']:
                            exclusive = True
                        
                        # rules in this rule set
                        if 'rules' in rule_set and rule_set['rules']:
                            pars = ProteinAnomalyRuleSet.objects.create(protein_anomaly=pa, exclusive=exclusive)
                            self.logger.info('Created protein anomaly rule set')
                            for rule in rule_set['rules']:
                                exp_keys = ['generic_number', 'amino_acid']
                                
                                # are all expected values specified for this rule
                                if all(x in rule for x in exp_keys) and all(rule[x] for x in exp_keys):
                                    # is this a negative rule (!= instead of ==)
                                    negative = False
                                    if rule['negative']:
                                        negative = True
                                    pargn, created = ResidueGenericNumber.objects.get_or_create(
                                        label=rule['generic_number'], protein_segment=ps, scheme=rns)
                                    if created:
                                        self.logger.info('Created generic_number {}'.format(pargn.label))
                                    par = ProteinAnomalyRule.objects.create(generic_number=pargn,
                                        rule_set=pars, amino_acid=rule['amino_acid'], negative=negative)
                                    self.logger.info('Created rule {} = {}, negative = {}'.format(
                                        par.generic_number.label, par.amino_acid, negative))
                                else:
                                    self.logger.error('Missing values for rule {:d} in file {}'.format((i+1),
                                        source_file))
        
        self.logger.info('COMPLETED CREATING PROTEIN ANOMALIES')