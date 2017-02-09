#!/usr/bin/env python
import sys, argparse, gzip, re, random, collections, inspect, os
from multiprocessing import Pool, cpu_count

from seqtools.statistics import average, median

def main(args):

  inf = sys.stdin
  if args.input != '-':
    if re.search('\.gz$',args.input):
      inf = gzip.open(args.input)
    else:
      inf = open(args.input)
  of = sys.stdout
  if args.output:
    of = open(args.output,'w')
  vals = []
  for line in inf:
    f = line.rstrip().split("\t")
    if args.full and f[4] != 'full':
      vals.append(None) 
      continue
    if args.gene:
      vals.append(f[2])
    elif args.transcript:
      vals.append(f[3])
  if args.original_read_count:
    if len(vals) > args.original_read_count:
      sys.stderr.write("ERROR: cant have a read count greater than the original read count\n")
      sys.exit()
    vals += [None]*(args.original_read_count-len(vals))
  # vals now holds an array to select from
  total = len(vals)
  xvals = make_sequence(total)
  # make shuffled arrays to use for each point
  qsvals = []
  if args.threads > 1:
    p = Pool(processes=args.threads)
  for i in range(0,args.samples_per_xval):
    if args.threads > 1:
      qsvals.append(p.apply_async(get_shuffled_array,args=(vals,)))
    else:
      qsvals.append(Queue(get_shuffled_array(vals)))
  if args.threads > 1:
    p.close()
    p.join()
  svals = [x.get() for x in qsvals] 

  second_threads = 1
  if second_threads > 1:
    p = Pool(processes=second_threads)
  results = []
  for xval in xvals:
    if second_threads > 1:
      r = p.apply_async(analyze_x,args=(xval,svals,args))
      results.append(r)
    else:
      r = Queue(analyze_x(xval,svals,args))
      results.append(r)
  if second_threads > 1:
    p.close()
    p.join()
  for r in [x.get() for x in results]:
    of.write("\t".join([str(x) for x in r])+"\n")
  inf.close()
  of.close()
class Queue:
  def __init__(self,val):
    self.val = val
  def get(self):
    return self.val

def get_shuffled_array(val):
  random.shuffle(val)
  return val[:]

# vals contains the annotation for each read

def analyze_x(xval,svals,args):
  s = args.samples_per_xval
  #cnts =  sorted(
  #          [len(
  #             [k for k in collections.Counter([z for z in [random.choice(vals) for y in range(0,xval)] if z]).values() if k >= args.min_depth]
  #           ) 
  #          for j in range(0,s)]
  #        )
  cnts = []
  for j in range(0,s):
    vals = svals[j][0:xval]
    cnts.append(len([x for x in collections.Counter([k for k in vals if k]).values() if x >= args.min_depth]))
  cnts = sorted(cnts)
  lower = float(cnts[int(len(cnts)*0.05)])
  mid = median(cnts)
  upper = float(cnts[int(len(cnts)*0.95)])
  #print len(vals)
  #print len([x for x in vals if x >0])
  #print cnts[0:5]
  #print cnts[-5:]
  #print [xval, lower, mid, upper]
  return [xval, lower, mid, upper]
  
def make_sequence(total):
  start = [1,2,3,4,5,10]
  while True:
    start += [x*10 for x in start[-5:]]
    if start[-1] > total: break
  return [x for x in start if x < total]+[total]

def do_inputs():
  parser = argparse.ArgumentParser(description="Take a locus bed file (bed) followed by locus id followed by read count.  Generate a rarefraction.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument('input',help="Use - for STDIN")
  parser.add_argument('-o','--output',help="Write output here")
  parser.add_argument('--threads',type=int,default=cpu_count(),help="INT threads to use")
  parser.add_argument('--original_read_count',type=int,help="INT allows accounting for unmapped reads not included here.")
  parser.add_argument('--samples_per_xval',type=int,default=1000,help="Sample this many times")
  parser.add_argument('--min_depth',type=int,default=1,help="Require at least this depth to count as a hit.")
  parser.add_argument('--full',action='store_true',help="Return full length matchs only")
  group1 = parser.add_mutually_exclusive_group(required=True)
  group1.add_argument('--gene',action='store_true',help="Gene based output")
  group1.add_argument('--transcript',action='store_true',help="Gene based output")
  args = parser.parse_args()
  return args

def external_cmd(cmd):
  cache_argv = sys.argv
  sys.argv = cmd.split()
  args = do_inputs()
  main(args)
  sys.argv = cache_argv

if __name__=="__main__":
  args = do_inputs()
  main(args)
